from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.db import models
from django.utils.translation import gettext_lazy as _
from django_rest_passwordreset.tokens import get_token_generator

STATE_CHOICES = (('basket', 'В корзине'),
                 ('confirmed', 'Подтвержден'),
                 ('assembled', 'Собран'),
                 ('sent', 'Отправлен'),
                 ('delivered', 'Выполнен'),
                 ('cancelled', 'Отменен'))
USER_TYPE_CHOICES = (('shop', 'Магазин'),
                     ('customer', 'Покупатель'))


class UserManager(BaseUserManager):
    """
    Миксин для управления пользователями
    """
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        """
        Create and save a user with the given username, email, and password.
        """
        if not email:
            raise ValueError('The given email must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self._create_user(email, password, **extra_fields)



class User(AbstractUser):
    """
    Стандартная модель пользователей
    """
    REQUIRED_FIELDS = []
    objects = UserManager()
    USERNAME_FIELD = 'email'
    email = models.EmailField(_('email address'), unique=True)
    company = models.CharField(verbose_name='Компания', max_length=40, blank=True)
    position = models.CharField(verbose_name='Должность', max_length=40, blank=True)
    username_validator = UnicodeUsernameValidator()
    username = models.CharField(
        _('username'),
        max_length=150,
        help_text=_('Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.'),
        validators=[username_validator],
        error_messages={
            'unique': _("A user with that username already exists."),
        },
    )

    is_active = models.BooleanField(
        _('active'),
        default=False,
        help_text=_(
            'Designates whether this user should be treated as active. '
            'Unselect this instead of deleting accounts.'
        ),
    )
    type = models.CharField(verbose_name='Тип пользователя', choices=USER_TYPE_CHOICES, max_length=5, default='buyer')

    def __str__(self):
        return f'{self.first_name} {self.last_name}'

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = "Список пользователей"
        ordering = ('email',)


class Shop(models.Model):
    name = models.CharField(max_length=50, verbose_name='Название')
    url = models.URLField(verbose_name='Ссылка', null=True, blank=True)
    user = models.OneToOneField(User, verbose_name='Пользователь',
                                blank=True, null=True,
                                on_delete=models.CASCADE)
    state = models.BooleanField(verbose_name='статус получения заказов', default=True)

    class Meta:
        verbose_name = 'Магазин'
        verbose_name_plural = "Список магазинов"
        ordering = ('-name',)

    def __str__(self):
        return self.name


class Category(models.Model):
    shops = models.ManyToManyField(related_name='shop_category', to=Shop)
    name = models.CharField(verbose_name="Категория", max_length=50)

    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'


class Product(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='shop', null=True)
    name = models.CharField(verbose_name='Название', max_length=50)


class ProductInfo(models.Model):
    product = models.ForeignKey(Product, related_name='product', on_delete=models.CASCADE)
    shop = models.ForeignKey(Shop, related_name='shop_product', on_delete=models.CASCADE)
    name = Product.name
    quantity = models.PositiveIntegerField(verbose_name="Количество")
    price = models.DecimalField(verbose_name='Цена', decimal_places=2, max_digits=10)
    price_rrc = models.DecimalField(verbose_name='Рекомендуемая розничная цена', decimal_places=2, max_digits=10)


class Parameter(models.Model):
    name = models.CharField("Название", max_length=100)

    def __str__(self):
        return self.name


class ProductParameter(models.Model):
    product_info = models.ForeignKey(ProductInfo, related_name='product_info', on_delete=models.CASCADE, blank=True)
    parameter = models.ForeignKey(Parameter, verbose_name='Параметр', related_name='parameter',
                                  on_delete=models.CASCADE)
    value = models.CharField(verbose_name="Значение", max_length=300)


class Order(models.Model):
    user = models.ForeignKey(User, related_name='user_order', on_delete=models.CASCADE, blank=True)
    dt = models.DateTimeField()
    status = models.CharField(choices=STATE_CHOICES, max_length=50)

    class Meta:
        verbose_name = "Заказ"
        verbose_name_plural = "Заказы"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='order', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, related_name='product_order_item', on_delete=models.CASCADE)
    shop = models.ForeignKey(Shop, related_name='shop_order', on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        verbose_name = "Заказанная позиция"
        verbose_name_plural = "Список заказанных позиций"


class Contact(models.Model):
    user = models.ForeignKey(User, related_name='user_contact', on_delete=models.CASCADE, )
    city = models.CharField(verbose_name='Город', max_length=30)
    street = models.CharField(verbose_name='Улица', max_length=50)
    house = models.CharField(verbose_name='Дом', max_length=5)
    apartment = models.CharField(verbose_name='Квартира', null=True, max_length=5)
    phone = models.CharField(verbose_name='Телефон', max_length=15)
    email = models.CharField(verbose_name='Email', max_length=30)

    class Meta:
        verbose_name = "Контактная информация пользователя"
        verbose_name_plural = "Информация о контактах пользователей"

class ConfirmEmailToken(models.Model):
    class Meta:
        verbose_name = 'Токен подтверждения Email'
        verbose_name_plural = 'Токены подтверждения Email'

    @staticmethod
    def generate_key():
        """ generates a pseudo random code using os.urandom and binascii.hexlify """
        return get_token_generator().generate_token()

    user = models.ForeignKey(
        User,
        related_name='confirm_email_tokens',
        on_delete=models.CASCADE,
        verbose_name=_("The User which is associated to this password reset token")
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("When was this token generated")
    )

    # Key field, though it is not the primary key of the model
    key = models.CharField(
        _("Key"),
        max_length=64,
        db_index=True,
        unique=True
    )

    def save(self, *args, **kwargs):
        if not self.key:
            self.key = self.generate_key()
        return super(ConfirmEmailToken, self).save(*args, **kwargs)

    def __str__(self):
        return "Password reset token for user {user}".format(user=self.user)