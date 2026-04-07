from django.shortcuts import render
from django.views import View


class InventoryAppView(View):
    template_name = "inventory/app.html"

    def get(self, request):
        return render(request, self.template_name)
