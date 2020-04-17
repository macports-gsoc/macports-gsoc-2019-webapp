"""MacPorts URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.urls import path, include
from django.conf.urls import url
import views

urlpatterns = [
    path('', views.index, name='home'),
    path('statistics/', include('stats.urls')),
    path('maintainers/', include('maintainers.urls')),
    path('port/', include('port_detail.urls')),
    path('categories/', include('categories.urls')),
    path('variants/', include('variants.urls')),
    path('ports/search/', views.search, name='ports_search'),
    path('all_builds/', include('builds.urls')),
    path('api/v1/', include('api_v1.urls')),
    path('about/', views.about_page, name='about_page'),
]