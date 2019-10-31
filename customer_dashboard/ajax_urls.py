from django.conf.urls.defaults import *

urlpatterns = patterns('customer_dashboard.ajax_views',
                       (r'^edit_profile$','editProfile'),
                       (r'^edit_card$','editCard'),
)
  