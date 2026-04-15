from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

User = get_user_model()

# ── قائمة الدول ──
COUNTRY_CHOICES = [
    ('', '— اختر الدولة —'),
    ('NG', 'نيجيريا 🇳🇬'),
    ('NE', 'النيجر 🇳🇪'),
    ('GH', 'غانا 🇬🇭'),
    ('SD', 'السودان 🇸🇩'),
    ('SA', 'السعودية 🇸🇦'),
    ('EG', 'مصر 🇪🇬'),
    ('CM', 'الكاميرون 🇨🇲'),
    ('SN', 'السنغال 🇸🇳'),
    ('ML', 'مالي 🇲🇱'),
    ('BF', 'بوركينا فاسو 🇧🇫'),
    ('TD', 'تشاد 🇹🇩'),
    ('LY', 'ليبيا 🇱🇾'),
    ('MA', 'المغرب 🇲🇦'),
    ('SO', 'الصومال 🇸🇴'),
    ('ET', 'إثيوبيا 🇪🇹'),
    ('GB', 'المملكة المتحدة 🇬🇧'),
    ('US', 'الولايات المتحدة 🇺🇸'),
    ('CA', 'كندا 🇨🇦'),
    ('DE', 'ألمانيا 🇩🇪'),
    ('FR', 'فرنسا 🇫🇷'),
    ('OTHER', 'دولة أخرى...'),
]


class CustomUserCreationForm(UserCreationForm):
    name = forms.CharField(
        max_length=150,
        required=True,
        label=_("الاسم الكامل"),
        widget=forms.TextInput(attrs={'autocomplete': 'name', 'placeholder': ' '})
    )
    email = forms.EmailField(
        required=True,
        label=_("البريد الإلكتروني"),
        widget=forms.EmailInput(attrs={'autocomplete': 'email', 'placeholder': ' '})
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("name", "username", "email", "password1", "password2")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in self.fields:
            self.fields[field_name].help_text = ''
            self.fields[field_name].widget.attrs.setdefault('placeholder', ' ')

    def _post_clean(self):
        super(UserCreationForm, self)._post_clean()
        password = self.cleaned_data.get('password1')
        if password and len(password) < 4:
            self.add_error('password1',
                ValidationError(_('يجب أن لا تقل كلمة المرور عن 4 أحرف.')))

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError(_('هذا البريد الإلكتروني مستخدم بالفعل.'))
        return email

    def clean_username(self):
        username = self.cleaned_data.get('username', '').strip()
        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError(_('اسم المستخدم هذا مستخدم بالفعل.'))
        return username

    def save(self, commit=True):
        user = super(UserCreationForm, self).save(commit=False)
        user.set_password(self.cleaned_data['password1'])
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['name']
        if commit:
            user.save()
        return user


class ProfileEditForm(forms.Form):
    # ── بيانات المستخدم الأساسية ──
    name = forms.CharField(
        max_length=150,
        required=False,
        label=_("الاسم الكامل (Display Name)"),
    )
    username = forms.CharField(
        max_length=150,
        required=True,
        label=_("اسم المستخدم (Username)"),
    )
    email = forms.EmailField(
        required=True,
        label=_("البريد الإلكتروني (Email)"),
    )

    # ── بيانات البروفايل ──
    avatar = forms.ImageField(
        required=False,
        label=_("الصورة الشخصية"),
    )
    country = forms.ChoiceField(
        choices=COUNTRY_CHOICES,
        required=False,
        label=_("الدولة"),
    )
    birth_day = forms.IntegerField(
        required=False,
        label=_("اليوم"),
        min_value=1, max_value=31,
        widget=forms.NumberInput(attrs={'placeholder': 'اليوم'})
    )
    birth_month = forms.IntegerField(
        required=False,
        label=_("الشهر"),
        min_value=1, max_value=12,
        widget=forms.NumberInput(attrs={'placeholder': 'الشهر'})
    )
    birth_year = forms.IntegerField(
        required=False,
        label=_("السنة"),
        min_value=1900, max_value=2020,
        widget=forms.NumberInput(attrs={'placeholder': 'السنة'})
    )

    # ── كلمة المرور ──
    current_password = forms.CharField(
        required=False,
        label=_("كلمة المرور الحالية"),
        widget=forms.PasswordInput(attrs={'autocomplete': 'current-password'}),
    )
    new_password = forms.CharField(
        required=False,
        label=_("كلمة المرور الجديدة"),
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
    )
    confirm_password = forms.CharField(
        required=False,
        label=_("تأكيد كلمة المرور الجديدة"),
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        # Pre-fill من البيانات الموجودة
        self.fields['name'].initial = user.first_name
        self.fields['username'].initial = user.username
        self.fields['email'].initial = user.email
        # Profile fields
        profile = getattr(user, 'profile', None)
        if profile:
            self.fields['country'].initial = profile.country or ''
            if profile.birth_date:
                self.fields['birth_day'].initial = profile.birth_date.day
                self.fields['birth_month'].initial = profile.birth_date.month
                self.fields['birth_year'].initial = profile.birth_date.year

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        qs = User.objects.filter(email__iexact=email).exclude(pk=self.user.pk)
        if qs.exists():
            raise ValidationError(_('Wannan adireshin email yana amfani da shi.'))
        return email

    def clean_username(self):
        username = self.cleaned_data.get('username', '').strip()
        qs = User.objects.filter(username__iexact=username).exclude(pk=self.user.pk)
        if qs.exists():
            raise ValidationError(_('Wannan sunan mai amfani yana amfani da shi.'))
        return username

    def clean(self):
        cleaned = super().clean()
        new_pw = cleaned.get('new_password')
        confirm_pw = cleaned.get('confirm_password')
        current_pw = cleaned.get('current_password')

        if new_pw or confirm_pw or current_pw:
            # لازم يكتب الباسورد القديم
            if not current_pw:
                self.add_error('current_password',
                    _('يجب عليك كتابة كلمة المرور الحالية.'))
            elif not self.user.check_password(current_pw):
                self.add_error('current_password',
                    _('كلمة المرور الحالية غير صحيحة. حاول مرة أخرى.'))
            # تأكيد الجديد
            if new_pw and len(new_pw) < 4:
                self.add_error('new_password',
                    _('يجب أن لا تقل كلمة المرور عن 4 أحرف.'))
            if new_pw and new_pw != confirm_pw:
                self.add_error('confirm_password',
                    _('كلمتا المرور غير متطابقتين.'))
        return cleaned

    def save(self, files=None):
        from .models import UserProfile
        import datetime

        data = self.cleaned_data
        user = self.user

        # حفظ بيانات User
        user.first_name = data.get('name', '')
        user.username = data.get('username', user.username)
        user.email = data.get('email', user.email)

        # تغيير كلمة المرور لو اختار
        new_pw = data.get('new_password')
        if new_pw:
            user.set_password(new_pw)

        user.save()

        # حفظ UserProfile
        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.country = data.get('country') or None

        # تاريخ الميلاد
        day = data.get('birth_day')
        month = data.get('birth_month')
        year = data.get('birth_year')
        if day and month and year:
            try:
                profile.birth_date = datetime.date(year, month, day)
            except ValueError:
                pass
        else:
            profile.birth_date = None

        # الصورة
        if files and 'avatar' in files and files['avatar']:
            profile.avatar = files['avatar']

        profile.save()
        return user