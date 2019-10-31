import datetime
from django import forms
from django.utils.translation import ugettext_lazy as _
from book_trip import models #import BookTripSession
from book_trip import rexHelperFunctions #import isCouponCodeValid

PASSENGER_COUNTS = (
	('1','1'),
	('2','2'),
	('3','3'),
	('4','4'),
	('5','5'),
	('6','6'),
	('7','7'),
	('8','8'),
	('9','9'),
	('10','10'),
	('11','11'),
	('12','12'),
	('13','13'),
	('14','14'),
	('15','15'),
	('16','16'),
	('17','17'),
	('18','18'),
	('19','19'),
	('20','20'),
)


class BookNowForm(forms.ModelForm):
	adult_count = forms.ChoiceField(choices=PASSENGER_COUNTS)
#	children_count = forms.ChoiceField(choices=PASSENGER_COUNTS)
#	student_count = forms.ChoiceField(choices=PASSENGER_COUNTS)
#	senior_count = forms.ChoiceField(choices=PASSENGER_COUNTS)


	def __init__(self, timeChoices, *args, **kwargs):
		super(BookNowForm,self).__init__(*args, **kwargs)

		# Add time frame
		times = []
		for token in timeChoices:
			keyTuple = (token.key, token.name)
			times.append(keyTuple)

		# departure time
		self.fields['departure_time'] = forms.ChoiceField(choices=times)
		self.fields['return_time'] = forms.ChoiceField(choices=times)

	def clean(self):
		cleaned_data = self.cleaned_data

		origin_rex_key = cleaned_data.get('origin_rex_key')
		departure_date = cleaned_data.get('departure_date')
		adult_count = cleaned_data.get('adult_count')
#		children_count = cleaned_data.get('children_count')
#		senior_count = cleaned_data.get('senior_count')
		return_date = cleaned_data.get('return_date')
		is_one_way = cleaned_data.get('is_one_way')

		if origin_rex_key == '0':
			msg = u"You must enter a valid point of departure."
			self._errors['origin_rex_key'] = self.error_class([msg])

		if departure_date is None:
			msg = u"You must enter a valid departure date."
			self._errors['departure_date'] = self.error_class([msg])

		if (departure_date is not None) and departure_date < datetime.date.today():
			msg = u"You must enter a departure date on or after today."
			self._errors['departure_date'] = self.error_class([msg])

		if is_one_way:
			if self.errors.has_key('return_date'):
				del self.errors['return_date']

		else :
			if return_date is None:
				msg = u"You must enter a valid return date, or select one way."
				self._errors['return_date'] = self.error_class([msg])

			if not (return_date is None) and departure_date > return_date:
				msg = u"You must choose a date on or after your departure date"
				self._errors['return_date'] = self.error_class([msg])


		# Check for valid coupon code
		couponCode = cleaned_data.get('promo_code')

		if len(couponCode) > 0:

			isValid = rexHelperFunctions.isCouponCodeValid(couponCode)
			if not isValid:
				msg = u"The coupon code is invalid."
				self._errors['promo_code'] = self.error_class([msg])


		return cleaned_data



	class Meta:
		model = models.BookTripSession
		fields = ('origin_rex_key','departure_date','departure_time','destination_rex_key','return_date','return_time',
		          'is_one_way','adult_count','promo_code')


CARD_CHOICES = (
	('VISA','Visa'),
    ('MC','Mastercard'),
    ('AMX','American Express')
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

class PaymentForm(forms.Form):

	#If Default Card
	charge_to_default = forms.BooleanField(required=False)

	#Billing Address
	first_name = forms.CharField(label=_("First Name"), required=True)
	last_name = forms.CharField(label=_("Last Name"), required=True)
	address = forms.CharField(label=_("Address"), required=True)
	unit = forms.CharField(label=_("Unit"), required=False)
	city = forms.CharField(label=_("City"), required=True)
	province_state = forms.CharField(label=_("Province State"), required=True)
	country = forms.CharField(label=_("Country"), required=True)
	postal_code = forms.CharField(label=_("Postal Code"), required=True)

	#Credit Card Information
	set_default = forms.BooleanField(required=False)
	card_type = forms.ChoiceField(choices=CARD_CHOICES, required=True)
	card_number = forms.CharField(label=_("Card Number"), required=True)
	exp_month = forms.ChoiceField(choices=EXP_MONTHS, required=True)
	#exp_year = forms.ChoiceField(choices='', required=True)
	security_number = forms.CharField(label=_("Security Number"), required=True)
	terms = forms.BooleanField(required=True)
	email = forms.EmailField(required=True, max_length=100)
	email_verify = forms.EmailField(required=True, max_length=100)


	def __init__(self, *args, **kwargs):
		super(PaymentForm,self).__init__(*args, **kwargs)

		# Add years field
		this_year = datetime.date.today().year
		years = range(this_year, this_year+10)

		year_choices = []
		for year in years:
			selection = (year, year)
			year_choices.append(selection)

		self.fields['exp_year'] = forms.ChoiceField(choices=year_choices, required=True)

		
	def clean(self):
		cleaned_data = self.cleaned_data

		#If there are already errors then no need to go further.
		if len(self._errors) > 0:
			return cleaned_data

		email = cleaned_data.get('email')
		email_verify = cleaned_data.get('email_verify')

		if email != email_verify:
			raise forms.ValidationError("Please check your email address. The 'email' and 're-enter email' values do not match.")

		return cleaned_data


class TravelerProfilesForm(forms.Form):
	first_name = forms.CharField(label=_("First Name"), required=True)
	last_name = forms.CharField(label=_("Last Name"), required=True)
	email = forms.EmailField(label=_("Email"), required=True)

	def clean(self):
		cleaned_data = self.cleaned_data

		#If there are already errors then no need to go further.
		if len(self._errors) > 0:
			return cleaned_data

		return cleaned_data