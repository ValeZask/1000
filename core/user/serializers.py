from rest_framework import serializers
from .models import MyUser, PasswordResetCode
from django.core.mail import send_mail
from django.conf import settings


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = MyUser
        fields = ('email', 'username', 'phone_number', 'password', 'password_confirm')

    def validate(self, data):
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError({"password_confirm": "Пароли не совпадают."})
        return data

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        user = MyUser.objects.create_user(
            email=validated_data['email'],
            username=validated_data['username'],
            phone_number=validated_data.get('phone_number'),
            password=validated_data['password']
        )
        return user


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = MyUser
        fields = ('id', 'email', 'username', 'phone_number', 'address', 'cover')
        read_only_fields = ('id', 'email')

    def validate_phone_number(self, value):
        if value and len(value) < 10:
            raise serializers.ValidationError("Номер телефона слишком короткий.")
        return value

    def validate_username(self, value):
        if self.instance and self.instance.username != value:
            if MyUser.objects.filter(username=value).exclude(id=self.instance.id).exists():
                raise serializers.ValidationError("Пользователь с таким именем уже существует.")
        return value


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        if not MyUser.objects.filter(email=value).exists():
            raise serializers.ValidationError("Пользователь с таким email не найден.")
        return value

    def save(self):
        email = self.validated_data['email']
        user = MyUser.objects.get(email=email)
        reset_code = PasswordResetCode.objects.create(user=user)
        subject = 'Сброс пароля'
        message = f'Ваш код для сброса пароля: {reset_code.code}\nКод действителен 15 минут.'
        from_email = settings.DEFAULT_FROM_EMAIL
        recipient_list = [email]
        send_mail(subject, message, from_email, recipient_list)
        return reset_code

class PasswordResetConfirmSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=6, min_length=6)
    new_password = serializers.CharField(min_length=8, write_only=True)
    new_password_confirm = serializers.CharField(min_length=8, write_only=True)

    def validate(self, data):
        if data['new_password'] != data['new_password_confirm']:
            raise serializers.ValidationError({"new_password_confirm": "Пароли не совпадают."})
        try:
            reset_code = PasswordResetCode.objects.get(code=data['code'])
        except PasswordResetCode.DoesNotExist:
            raise serializers.ValidationError({"code": "Неверный или несуществующий код."})
        if reset_code.is_expired():
            raise serializers.ValidationError({"code": "Срок действия кода истёк."})
        return data

    def save(self):
        code = self.validated_data['code']
        reset_code = PasswordResetCode.objects.get(code=code)
        user = reset_code.user
        user.set_password(self.validated_data['new_password'])
        user.save()
        reset_code.delete()
        return user
