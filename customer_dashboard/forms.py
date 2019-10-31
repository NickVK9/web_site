from datetime import date, datetime
from django import forms
from django.contrib.localflavor.ca.ca_provinces import PROVINCE_CHOICES
from django.contrib.localflavor.ca.forms import CAProvinceSelect, CAProvinceField
from django.contrib.localflavor.fr.forms import FRPhoneNumberField
from django.contrib.localflavor.us.forms import USStateField
from django.contrib.localflavor.us.us_states import STATE_CHOICES
from django.utils.translation import ugettext_lazy as _


class AddTravellerProfileForm(forms.Form):
	firstName = forms.CharField(label=_("First Name"), required=True)
	lastName = forms.CharField(label=_("Last Name"), required=True)
	phoneDay = forms.CharField(label=_("Phone Number"), required=True)


COUNTRIES = (
	('default','--SELECT--'),
	('Canada','Canada'),
	('US','United States'),
)


class EditTravellerProfileForm(forms.Form):
	key = forms.CharField(max_length=200)
	firstName = forms.CharField(label=_("First Name"), required=True)
	lastName = forms.CharField(label=_("Last Name"), required=True)
	street = forms.CharField(label=_("Address1"), required=False)
	street2 = forms.CharField(label=_("Address2"), required=False)
	city = forms.CharField(label=_("City"), required=False)
	postal = forms.CharField(label=_("Postal Code"), required=False)
	country = forms.ChoiceField(choices=COUNTRIES, required=False)

	YOUR_STATE_CHOICES = list(STATE_CHOICES)
	YOUR_STATE_CHOICES.insert(0, ('', '---------'))
	state = USStateField(required=False, widget=forms.Select(choices=YOUR_STATE_CHOICES))

	YOUR_PROVINCE_CHOICES = list(PROVINCE_CHOICES)
	YOUR_PROVINCE_CHOICES.insert(0, ('', '---------'))
	province = CAProvinceField(required=False, widget=forms.Select(choices=YOUR_PROVINCE_CHOICES))

	email = forms.EmailField(required=False)
	phoneDay = forms.CharField(label=_("Phone Number"), required=True)
	phoneEve = forms.CharField(label=_("Cell Phone"), required=False)
	is_ama = forms.BooleanField(required=False)
	ama = forms.CharField(label=_("AMA"), required=False)
	ama_expiration = forms.CharField(label=_("AMA Expiration"), required=False)
	is_student = forms.BooleanField(required=False)
	student = forms.CharField(label=_("Student"), required=False)
	student_expiration = forms.CharField(label=_("Student Expiration"), required=False)

	mobility_impaired = forms.BooleanField(required=False)
	wheelchair = forms.BooleanField(required=False)
	visual_impaired = forms.BooleanField(required=False)
	hearing_impaired = forms.BooleanField(required=False)



	def clean(self):
		cleaned_data = self.cleaned_data

		#If there are already errors then no need to go further.
		if len(self._errors) > 0:
			return cleaned_data

		return cleaned_data




CARD_CHOICES = (
	('Visa','Visa'),
    ('MasterCard','Mastercard'),
    ('Amex','American Express')
)

EXP_MONTHS = (
	('01','01 - JAN'),
	('02','02 - FEB'),
    ('03','03 - MAR'),
    ('04','04 - APR'),
    ('05','05 - MAY'),
    ('06','06 - JUN'),
    ('07','07 - JUL'),
    ('08','08 - AUG'),
    ('09','09 - SEP'),
    ('10','10 - OCT'),
    ('11','11 - NOV'),
    ('12','12 - DEC')
)

class CreditCardEditForm(forms.Form):
	EXP_YEAR = [(x, x) for x in xrange(date.today().year,
                                       date.today().year + 15)]

	
	holder = forms.CharField(max_length=60, required=True)
	brand = forms.ChoiceField(choices=CARD_CHOICES, required=True)
	number = forms.CharField(label=_("Card Number"), required=True)
	exp_month = forms.ChoiceField(choices=EXP_MONTHS, required=True)
	exp_year = forms.ChoiceField(choices=EXP_YEAR, required=True)
	key = forms.CharField(required=False)
	


