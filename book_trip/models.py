from decimal import Decimal
import logging
from django.db import models

TRIP_SESSION_STATUS_CHOICES = (
	('OPEN', 'Open'),
	('CLOSED', 'Closed'),
)


class BookTripSession(models.Model):
	origin_rex_key = models.CharField(max_length=20, blank=True, null=True)
	origin_label = models.CharField(max_length=100, blank=True, null=True)
	departure_date = models.DateField(blank=True, null=True)

	departure_time = models.CharField(max_length=20, blank=True, null=True)

	destination_rex_key = models.CharField(max_length=20, blank=True, null=True)
	destination_label = models.CharField(max_length=100, blank=True, null=True)
	return_date = models.DateField(blank=True, null=True)
	return_time = models.CharField(max_length=20, blank=True, null=True)

	is_one_way = models.BooleanField(default=False)

	adult_count = models.IntegerField(default=0)
	children_count = models.IntegerField(default=0)
	student_count = models.IntegerField(default=0)
	senior_count = models.IntegerField(default=0)

	promo_code = models.CharField(max_length=20, blank=True, null=True)

	create_date = models.DateTimeField(auto_now_add=True)
	last_modified_date = models.DateTimeField(auto_now=True)

	origin_trip = models.ForeignKey('Trip', related_name='origin_trip_session', blank=True, null=True,
	                                on_delete=models.SET_NULL)
	return_trip = models.ForeignKey('Trip', related_name='return_trip_session', blank=True, null=True,
	                                on_delete=models.SET_NULL)

	ticket_total = models.DecimalField(decimal_places=2, max_digits=10, default='0.00')
	tax_total = models.DecimalField(decimal_places=2, max_digits=10, default='0.00')
	discount_total = models.DecimalField(decimal_places=2, max_digits=10, default='0.00')
	grand_total = models.DecimalField(decimal_places=2, max_digits=10, default='0.00')
	reward_points = models.IntegerField(default=0)
	status = models.CharField(max_length=20, choices=TRIP_SESSION_STATUS_CHOICES, default='OPEN')

	sales_order_rex_key = models.CharField(max_length=30, blank=True, null=True)

	pickled_rex_booking_session = models.TextField(blank=True, null=True)

	def session_can_checkout(self):

		if self.passenger_info_is_missing():
			return False

		if self.origin_trip is None:
			return False

		if not (self.status == 'OPEN'):
			return False

		return True


	def passenger_info_is_missing(self):

		passCount = 0
		for passenger in self.traveler_profiles.all():
			passCount += 1
			if passenger.info_is_missing():
				return True

		if passCount < 1:
			return True

		return False


	def set_origin_rex_key(self, originKey):

		if self.origin_rex_key == originKey:
			return

		self.origin_label = None
		self.destination_rex_key = None
		self.destination_label = None
		self.origin_trip = None
		self.return_trip = None

		# Reset Pricing
		self.ticket_total = Decimal('0.00')
		self.discount_total = Decimal('0.00')
		self.tax_total = Decimal('0.00')
		self.grand_total = Decimal('0.00')

		#Clear out any choices for the old origin
		self.trips.all().delete()

		self.origin_rex_key = originKey


	def set_destination_rex_key(self, destKey):

		if self.destination_rex_key == destKey:
			return

		self.origin_trip = None
		self.return_trip = None
		self.trips.all().delete()
		self.destination_rex_key = destKey
		self.destination_label = None


	def update_from_rex_booking(self, rexBooking):
		self.ticket_total = rexBooking.billing.price

	def departure_month_zero_index(self):
		return self.departure_date.month - 1

	def return_month_zero_index(self):
		return self.return_date.month - 1

	def initialize_traveler_profiles(self):

		# Adults
		self.setup_default_profiles_for_traveller_class('ADULT', self.adult_count)

		# Children
		self.setup_default_profiles_for_traveller_class('CHILD', self.children_count)

		# Students
		self.setup_default_profiles_for_traveller_class('STUDENT', self.student_count)

		# Seniors
		self.setup_default_profiles_for_traveller_class('SENIOR', self.senior_count)


	def setup_default_profiles_for_traveller_class(self, traveler_class, traveler_count):

		# see if we already have traveler profiles
		travelers = self.traveler_profiles.all().filter(traveler_class=traveler_class)

		if len(travelers) == traveler_count:
			# if we already have the right number then just return
			return

		# clear out the ones we have now and re-create them
		if len(travelers) > 0:
			travelers.delete()

		for index in range(1, traveler_count + 1):
			label = "%s%s" % (traveler_class, index)
			traveler_profile = TravelerProfile()
			traveler_profile.first_name = ''
			traveler_profile.last_name = label
			traveler_profile.traveler_class = traveler_class
			traveler_profile.bookTripSession = self
			traveler_profile.save()

	def trip_selected(self, aTrip):

		aTrip.seat_assignments.all().delete()

		if aTrip.origin_key == self.origin_rex_key:

			logging.info('Setting origin trip')

			if self.origin_trip != None:
				Trip_Traveller_Seat.objects.filter(trip=self.origin_trip).delete()

			self.origin_trip = aTrip

		#if aTrip.origin_key == self.destination_rex_key:
		else:
			logging.info('Setting return trip')

			if self.return_trip != None:
				Trip_Traveller_Seat.objects.filter(trip=self.return_trip).delete()

			self.return_trip = aTrip

		# Initialize traveller seating preferences
		for travelerProfile in self.traveler_profiles.all():
			logging.info('Creating Trip / Traveller / Seat Assignment')

			seat_sel = Trip_Traveller_Seat(trip=aTrip, travelerProfile=travelerProfile,
			                               seat_no="None")
			seat_sel.save()


		# Reset Pricing
		self.ticket_total = Decimal('0.00')
		self.tax_total = Decimal('0.00')
		self.grand_total = Decimal('0.00')


	def clear_trips_from_this_location(self, aRexOriginKey):

		self.trips.all().filter(origin_key=aRexOriginKey).delete()


	def allow_step_2(self):
		if len(self.traveler_profiles.all()) < 1:
			return False
		return True


	def allow_step_3(self):
		if self.origin_trip != None:
			return True
		return False


	def allow_step_4(self):
		if self.passenger_info_is_missing():
			return False
		return True


	def passenger_count(self):
		if self.traveler_profiles:
			return self.traveler_profiles.count()
		return 0



	class Meta:
		ordering = ['-create_date']


class Trip(models.Model):
	bookTripSession = models.ForeignKey('BookTripSession', related_name='trips', on_delete=models.DO_NOTHING)
	facility_key = models.CharField(max_length=100, blank=True, null=True)
	facility_name = models.CharField(max_length=200, blank=True, null=True)
	product_key = models.CharField(max_length=100, blank=True, null=True)
	product_name = models.CharField(max_length=200, blank=True, null=True)
	origin_key = models.CharField(max_length=100, blank=True, null=True)
	origin_name = models.CharField(max_length=100, blank=True, null=True)
	destination_key = models.CharField(max_length=100, blank=True, null=True)
	destination_name = models.CharField(max_length=100, blank=True, null=True)
	depart_date = models.DateField()
	depart_time = models.CharField(max_length=20, blank=True, null=True)
	arrive_date = models.DateField()
	arrive_time = models.CharField(max_length=20, blank=True, null=True)
	carrier_key = models.CharField(max_length=100, blank=True, null=True)
	carrier_name = models.CharField(max_length=100, blank=True, null=True)
	route_key = models.CharField(max_length=100, blank=True, null=True)
	route_name = models.CharField(max_length=100, blank=True, null=True)
	average_price = models.DecimalField(max_digits=10, decimal_places=2)
	duration = models.CharField(max_length=30, blank=True, null=True)
	parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='trip_legs')
	rex_crs = models.CharField(max_length=60, blank=True, null=True)
	allow_pick_seats = models.BooleanField()
	alert_msg_img_url = models.CharField(max_length=400, blank=True, null=True)


	def hasComponentTripLegs(self):
		if len(self.trip_legs.all()) > 0:
			return True

		return False


	def stopCount(self):
		stopCount = len(self.trip_legs.all())

		if stopCount < 1:
			return "non-stop"

		return stopCount - 1

	def InitializeFromRexTrip(self, book_session, rex_trip):

		self.bookTripSession = book_session

		self.facility_key = rex_trip.facility.key
		self.facility_name = rex_trip.facility.name
		self.product_key = rex_trip.product.key
		self.product_name = rex_trip.product.name
		self.origin_key = rex_trip.origin.key
		self.origin_name = rex_trip.origin.name
		self.destination_key = rex_trip.destination.key
		self.destination_name = rex_trip.destination.name
		self.depart_date = rex_trip.depart_date
		self.depart_time = rex_trip.depart_time
		self.arrive_date = rex_trip.arrive_date
		self.arrive_time = rex_trip.arrive_time

		self.carrier_name = rex_trip.carrier
		self.route_key = rex_trip.route
		self.route_name = rex_trip.route
		self.rex_crs = rex_trip.crs
		self.allow_pick_seats = rex_trip.assignable
		self.alert_msg_img_url = rex_trip.booking_alert_image

		#self.rex_xml = rex_trip.xml

		try:
			self.average_price = str(rex_trip.average_price())
		except:
			self.average_price = "0.00"

		self.duration = rex_trip.duration


TRAVELER_CLASSIFICATIONS = (
	('ADULT', 'Adult'),
	('CHILD', 'Child'),
	('STUDENT', 'Student'),
	('SENIOR', 'Senior')
)


class TravelerProfile(models.Model):
	bookTripSession = models.ForeignKey('BookTripSession', on_delete=models.CASCADE, related_name='traveler_profiles')
	rex_key = models.CharField(max_length=20, blank=True, null=True)
	traveler_class = models.CharField(max_length=20, choices=TRAVELER_CLASSIFICATIONS)
	first_name = models.CharField(max_length=100)
	last_name = models.CharField(max_length=100)
	age = models.IntegerField(default=0)
	phone = models.CharField(max_length=100)
	seat_assignments = models.ManyToManyField(Trip, through='Trip_Traveller_Seat')
	ticket_total = models.DecimalField(decimal_places=2, max_digits=10, default='0.00')


	def info_is_missing(self):

		if len(self.first_name) < 1:
			return True

		if len(self.last_name) < 1:
			return True

		if len(self.phone) < 1:
			return True

		return False


	def __unicode__(self):
		return "name: %s %s | class: %s | phone: %s " % (
		self.first_name, self.last_name, self.traveler_class, self.phone)


class Trip_Traveller_Seat(models.Model):
	trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='seat_assignments')
	travelerProfile = models.ForeignKey(TravelerProfile, on_delete=models.CASCADE)
	seat_no = models.CharField(max_length=10, blank=True, null=True)


	

