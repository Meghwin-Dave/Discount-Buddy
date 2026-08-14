from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import ensure_csrf_cookie

from .account_deletion import send_account_deletion_otp, delete_account_with_otp

REQUEST_SENT_MESSAGE = (
    "If an account exists for this email, we sent a 4-digit verification code. "
    "Enter it below to permanently delete the account and associated data."
)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class DeleteAccountPageView(View):
    """
    Public Google Play account-deletion page.

    Users who have uninstalled the app can request deletion by email,
    then confirm with the same OTP used by the in-app delete API.
    """

    template_name = "account_deletion/delete_account.html"

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name, {"step": "email"})

    def post(self, request, *args, **kwargs):
        action = (request.POST.get("action") or "request").strip()
        email = (request.POST.get("email") or "").strip()

        if action == "confirm":
            return self._confirm_deletion(request, email)

        return self._request_deletion(request, email)

    def _request_deletion(self, request, email):
        if not email:
            return render(
                request,
                self.template_name,
                {
                    "step": "email",
                    "error": "Please enter your registered email address.",
                    "email": email,
                },
            )

        send_account_deletion_otp(email)
        return render(
            request,
            self.template_name,
            {
                "step": "otp",
                "email": email,
                "info": REQUEST_SENT_MESSAGE,
            },
        )

    def _confirm_deletion(self, request, email):
        otp = (request.POST.get("otp") or "").strip()
        if not email:
            return render(
                request,
                self.template_name,
                {
                    "step": "email",
                    "error": "Please enter your registered email address.",
                },
            )

        success, error = delete_account_with_otp(email, otp)
        if success:
            return render(
                request,
                self.template_name,
                {"step": "done"},
            )

        return render(
            request,
            self.template_name,
            {
                "step": "otp",
                "email": email,
                "error": error,
                "info": REQUEST_SENT_MESSAGE,
            },
        )
