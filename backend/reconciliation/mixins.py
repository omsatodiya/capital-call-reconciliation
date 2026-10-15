from rest_framework.exceptions import NotFound, ParseError

from .models import Organization


class OrganizationScopedMixin:
    # Runs before every handler (get, post, ...) and sets self.organization.

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        self.organization = self.get_organization(request)

    def get_organization(self, request):
        slug = request.headers.get("X-Organization", "").strip().lower()
        if not slug:
            raise ParseError("X-Organization header is required.")

        try:
            return Organization.objects.get(slug=slug)
        except Organization.DoesNotExist:
            raise NotFound("Organization not found.")