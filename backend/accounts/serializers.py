from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from accounts.models import User, WaitlistSignup


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'email', 'full_name', 'phone', 'address_for_service', 'role')
        read_only_fields = ('id', 'email', 'role')


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    class Meta:
        model = User
        fields = ('email', 'password', 'full_name', 'phone', 'address_for_service')

    def validate_email(self, value):
        email = value.strip().lower()
        if User.objects.filter(email=email).exists():
            raise serializers.ValidationError('An account with this email already exists.')
        return email

    def validate_password(self, value):
        validate_password(value)
        return value

    def create(self, validated_data):
        password = validated_data.pop('password')
        return User.objects.create_user(password=password, **validated_data)


class WaitlistSerializer(serializers.ModelSerializer):
    class Meta:
        model = WaitlistSignup
        fields = ('email', 'city')

    def validate_email(self, value):
        return value.strip().lower()
