from binascii import unhexlify
import logging
from django.core.exceptions import ObjectDoesNotExist
from django.core.validators import RegexValidator
from django.db import models
from django.utils import six
from django.utils.translation import ugettext_lazy as _

from django_otp import Device
from django_otp.oath import totp
from django_otp.util import hex_validator, random_hex
from two_factor.gateways import make_call, send_sms

phone_number_validator = RegexValidator(
    regex='^(\+|00)',
    message=_('Please enter a valid phone number, including your country code '
              'starting with + or 00.'),
)

PHONE_METHODS = (
    ('call', _('Phone Call')),
    ('sms', _('Text Message')),
)

logger = logging.getLogger(__name__)


class PhoneDevice(Device):
    number = models.CharField(max_length=16, validators=[phone_number_validator])
    key = models.CharField(max_length=40, validators=[hex_validator()],
                           default=lambda: random_hex(20),
                           help_text="Hex-encoded secret key")
    method = models.CharField(max_length=4, choices=PHONE_METHODS)

    @property
    def bin_key(self):
        return unhexlify(self.key.encode())

    def verify_token(self, token):
        for drift in range(-5, 1):
            if totp(self.bin_key, drift=drift) == token:
                return True
        return False

    def generate_challenge(self):
        """
        Sends the current TOTP token to `self.number` using `self.method`.
        """
        token = '%06d' % totp(self.bin_key)
        if self.method == 'call':
            make_call(device=self, token=token)
        else:
            send_sms(device=self, token=token)

    def __unicode__(self):
        """
        See upstream PR: http://bitbucket.org/psagers/django-otp/pull-request/1
        """
        try:
            username = self.user.username
        except ObjectDoesNotExist:
            username = ''
        return six.u('{0}: {1}'.format(username, self.name))
