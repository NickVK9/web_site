from django.db import models
from django.contrib.auth.models import User
from customer_dashboard import rexHelperFunctions #import *

class UserProfile(models.Model):
	user = models.ForeignKey(User, on_delete=models.CASCADE, unique=True)
	rex_customer_name = models.CharField(max_length=100,null=True,blank=True)
	rex_customer_key = models.CharField(max_length=20, null=True, blank=True)

	rex_traveller_profiles_lazy = None
	rex_ticket_packs_lazy = None
	rex_customer_lazy = None
	rex_points_lazy = None


	def rex_customer(self):
		if self.rex_customer_lazy == None:
			self.rex_customer_lazy = getCustomer(self.rex_customer_key)

		return self.rex_customer_lazy
			

	def rex_traveller_profiles(self):
		if self.rex_traveller_profiles_lazy == None:
			self.rex_traveller_profiles_lazy = getCustomerProfiles(self.rex_customer_key, self.rex_customer_name)

		return self.rex_traveller_profiles_lazy
	

	def rex_ticket_packs(self):
		if self.rex_ticket_packs_lazy == None:
			self.rex_ticket_packs_lazy = getTicketPacks(self.rex_customer_key, self.rex_customer_name)

		return self.rex_ticket_packs_lazy

	def rex_points(self):
		if self.rex_points_lazy == None:
			self.rex_points_lazy = getCustomerPoints(self.rex_customer_key, self.rex_customer_name)

		return self.rex_points_lazy


	def display_name(self):

		name = self.user.username

		if len(name) > 13:
			name = name[0:10] + '..'

		return name


	def __unicode__(self):
		return u'Profile of user: %s' % self.user.username