from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin


class StaffGroupRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """
    T2.1: restricts a view to users in the 'personal' or 'admin' group
    (migration accounts.0003_create_groups already creates these), or
    Django staff/superusers. Plain 'customer' users get a 403.

    Combines LoginRequiredMixin so anonymous users are sent to the login
    page first, rather than getting a raw 403 for not being logged in.
    """

    permission_denied_message = "You don't have permission to access this page."

    def test_func(self):
        return self.request.user.is_staff_or_manager
