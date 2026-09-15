from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from .models import AuthToken


class PersonTokenAuthentication(BaseAuthentication):
    keyword = 'Token'

    def authenticate(self, request):
        auth = request.headers.get('Authorization', '')
        if not auth.startswith(f'{self.keyword} '):
            return None
        key = auth[len(self.keyword) + 1:].strip()
        if not key:
            return None
        try:
            token = AuthToken.objects.select_related('person').get(key=key)
        except AuthToken.DoesNotExist:
            raise AuthenticationFailed('Token inválido.')
        return (token.person, token)
