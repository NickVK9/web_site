from django.contrib import admin
from django.urls import reverse
from django.http import HttpResponseRedirect

from book_trip import models


def show_checkout_complete(modeladmin, request, queryset):
	book_session = queryset[0]
	assert isinstance(book_session, models.BookTripSession)
	if book_session.status != 'CLOSED':
		return

	request.session['book_trip_completed_session_id'] = book_session.id
	return HttpResponseRedirect(reverse("order-complete"))


class TravelerInline(admin.TabularInline):
	model = models.TravelerProfile


class BookTripSession_Admin(admin.ModelAdmin):
	list_display = ('origin_label', 'status', 'create_date', 'last_modified_date', 'adult_count')
	list_filter = ('status', 'create_date', 'last_modified_date')
	inlines = [
		TravelerInline,
	]
	actions = [show_checkout_complete,]


admin.site.register(models.BookTripSession, BookTripSession_Admin)
