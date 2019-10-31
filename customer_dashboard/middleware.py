class LazyUserProfile(object):
    def __get__(self, request, obj_type=None):
        if request.user.is_authenticated():
            if not hasattr(request, '_cached_userProfile'):
                from customer_dashboard.models import UserProfile

                profiles = UserProfile.objects.filter(user = request.user)

                if len(profiles) == 1:
                    request._cached_userProfile = profiles[0]
                else:
                    return None
            return request._cached_userProfile
        else:
            return None

class UserProfileMiddleware(object):
    def process_request(self,request):
        request.__class__.userProfile = LazyUserProfile()
        return None



