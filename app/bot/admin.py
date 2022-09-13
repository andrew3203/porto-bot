from django.contrib import admin
from django.http import HttpResponseRedirect, HttpResponseServerError
from django.shortcuts import render
from bot.models import User

from portobello.settings import DEBUG
from bot.handlers.utils import utils

from django.contrib.auth.models import Group as gp
from django.contrib.auth.models import User as DefaultUser

from django.urls import reverse


from bot import models
from bot import forms

from bot.tasks import broadcast_message2
from django_celery_beat.models import (
    IntervalSchedule,
    CrontabSchedule,
    SolarSchedule,
    ClockedSchedule,
    PeriodicTask,
)

admin.site.unregister(SolarSchedule)
admin.site.unregister(ClockedSchedule)
admin.site.unregister(PeriodicTask)
admin.site.unregister(IntervalSchedule)
admin.site.unregister(CrontabSchedule)

admin.site.unregister(gp)
admin.site.unregister(DefaultUser)


admin.site.site_header = 'Portobello Bot Админ панель'
admin.site.index_title = 'Portobello Bot Администратор'
admin.site.site_title = 'Admin'

@admin.register(DefaultUser)
class DjangoAdmin(admin.ModelAdmin):
    list_display = [
        'username', 'email', 'first_name',
        'is_staff', 'date_joined'
    ]
    list_filter = ["is_active", "is_staff"]
    search_fields = ('username', 'email')
    fieldsets = (
        ('О пользователе', {
            'fields': (
                ("username",),
                ("password",),
            ),
        }),
        ('Персональная информация', {
            'fields': (
                ("first_name"),
                ('last_name',),
                ("email",)
            ),
        }),
        ('Дополнительная информация', {
            'fields': (
                ("is_active",),
                ("is_staff", ),
                ('is_superuser',)
            ),
        }),
        ('Важные даты', {
            'fields': (
                ("date_joined",),
                ('last_login',)
            ),
        }),
    )
    readonly_fields = ('password',)

@admin.register(models.User)
class UserAdmin(admin.ModelAdmin):
    list_display = [
        'user_id', 'username', 'first_name', 'last_name',
        'language_code', 'deep_link',
        'created_at', 'updated_at', 'company', 'rating_place', 'turnover',
        'all_time_cashback', 'free_gold_tickets', 'free_cashback', 'all_time_gold_tickets'
    ]
    list_filter = ["is_blocked_bot", 'is_admin', 'position']
    search_fields = ('username', 'user_id')
    fieldsets = (
        ('Основное', {
            'fields': (
                ("user_id",),
                ('username', 'language_code'),
                ('first_name', 'last_name'),
                ('owner',)
            ),
        }),
        ('О пользователе (из crm)', {
            'fields': (
                ('company',),
                ('phone',),
                ('turnover', 'orders'),
                ('deep_link', 'position'),
                ("rating_place",),
                ('all_time_cashback', 'free_cashback'),
                ('free_gold_tickets', 'all_time_gold_tickets'),
            ),
        }),
        ('Дополнительная информация', {
            'fields': (
                ("is_blocked_bot",),
                ('is_admin',),
            ),
        }),
        ('Важные даты', {
            'fields': (
                ('created_at',),
                ('updated_at',)
            ),
        }),
    )
    readonly_fields = ('created_at', 'updated_at')

    def make_group(self, request, queryset):
        user_ids = queryset.values_list('user_id', flat=True)
        if 'apply' in request.POST:
            group = forms.MakeGroupForm(request.POST).save()
            url = reverse(f'admin:{group._meta.app_label}_{group._meta.model_name}_changelist')#, args=[group.id])
            return HttpResponseRedirect(url)

        else:
            form = forms.MakeGroupForm(initial={'_selected_action': user_ids, 'users': user_ids})
            return render(
                request, "admin/make_group.html", {
                    'form': form, 'title': u'Создание новой группы'}
            )

    def broadcast(self, request, queryset):
        # TODO: check the function
        """ Select users via check mark in django-admin panel, then select "Broadcast" to send message"""
        user_ids = queryset.values_list('user_id', flat=True).distinct().iterator()

        if 'apply' in request.POST:
            f = forms.BroadcastForm(request.POST, request.FILES)
            print(f)
            if f.is_valid(): 
                broadcast = f.save() 
            else:
                return HttpResponseServerError()
            
            if DEBUG:  
                self.message_user(request, f"Рассылка {len(queryset)} сообщений начата")
                for user_id in user_ids:
                    next_state = models.User.get_broadcast_next_states(user_id, broadcast.message.id)
                    prev_msg_id = utils.send_broadcast_message(
                        next_state=next_state,
                        user_id=user_id,
                    ) 
                    User.set_message_id(user_id, prev_msg_id)

            else:

                self.message_user(request, f"Рассылка {len(queryset)} сообщений начата")
                broadcast_message2.delay(text=broadcast.text, user_ids=list(user_ids), message_id=broadcast.message.id) # TODO
                
            url = reverse(f'admin:{broadcast._meta.app_label}_{broadcast._meta.model_name}_changelist')
            return HttpResponseRedirect(url)
        else:
            user_ids = queryset.values_list('user_id', flat=True)
            form = forms.BroadcastForm(initial={'_selected_action': user_ids, 'users': user_ids})
            return render(
                request, "admin/broadcast_message.html", {
                    'form': form, 
                    'title': u'Создание рассылки сообщений'
                }
            )
    
    def set_owner(self, request, queryset):
        user_ids = queryset.values_list('user_id', flat=True)
        if 'apply' in request.POST:
            owner = request.POST["owner"]
            queryset.update(owner=owner)
            self.message_user(request, f"Менеджер для {len(queryset)} клиентов назначен")

        else:
            form = forms.SetOwnerForm(initial={'_selected_action': user_ids})
            return render(
                request, "admin/set_owner.html", {
                    'form': form, 'title': u'Назначение менеджера'}
            )

    actions = [broadcast, set_owner]
    broadcast.short_description = 'Создать рассылку'
    set_owner.short_description = 'Назначить менеджера'


@admin.register(models.Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'pk', 'message_type', 'clicks', 'group', 'updated_at', 'created_at'
    ]
    list_filter = ["message_type", "group"]
    search_fields = ('name', )
    fieldsets = (
        ('Основное', {
            'fields': (
                ("name", 'pk'),
                ('text',),
                ('message_type',),
                ('clicks', 'unic_clicks')
            ),
        }),
        ('Ограничения', {
            'fields': (
                #("group",),

            ),
        }),
        ('Медия', {
            'fields': (
                ("files",),
            ),
        }),
        ('Важные даты', {
            'fields': (
                ('created_at',),
                ('updated_at',)
            ),
        }),
    )
    readonly_fields = ('created_at', 'updated_at', 'pk')
    filter_horizontal = ('files',)

@admin.register(models.Broadcast)
class BroadcastAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'created_at'
    ]
    search_fields = ('name', 'tg_id')
    fieldsets = (
        ('Основное', {
            'fields': (
                ("name",),
                ("message",),
            ),
        }),
        ('Пользователи и группы', {
            'fields': (
                ("users",),
                #('group',),
            ),
        }),
        ('Важные даты', {
            'fields': (
                ('created_at',)
            ),
        }),
    )
    filter_horizontal = ('users',)
    readonly_fields = ('created_at',)

    def send_mailing(self, request, queryset):
        self.message_user(request, f"Рассылка {len(queryset)} сообщений начата!")
        for broadast in queryset:
            user_ids = broadast.users.all().values_list('user_id', flat=True)
            broadcast_message2.delay(text=broadast.text, user_ids=list(user_ids), message_id=broadast.message.id)

    actions = [send_mailing]
    send_mailing.short_description = 'Начать рассылку'


@admin.register(models.File)
class FileAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'tg_id', 'file', 'created_at'
    ]
    search_fields = ('name', 'tg_id')
    fieldsets = (
        ('Основное', {
            'fields': (
                ("name",),
                ("tg_id",),
            ),
        }),
        ('Информация о файле', {
            'fields': (
                ("file"),
                ('created_at',),
            ),
        })
    )
    readonly_fields = ('created_at',)

@admin.register(models.Poll)
class PollAdmin(admin.ModelAdmin):
    list_display = [
        'message', 'created_at'
    ]
    search_fields = ('message',)
    fieldsets = (
        ('Основное', {
            'fields': (
                ("message",),
                ("answers",),
            ),
        }),
        ('Важные даты', {
            'fields': (
                ("created_at"),
                ('updated_at',),
            ),
        })
    )
    readonly_fields = ('created_at','updated_at')


#@admin.register(models.Group)
#class GroupAdmin(admin.ModelAdmin):
#    list_display = [
#        'name', 'created_at'
#    ]
#    search_fields = ('name',)
#    fieldsets = (
#        ('Основное', {
#            'fields': (
#                ("name",),
#            ),
#        }),
#        ('Пользователи', {
#            'fields': (
#                ("users",),
#            ),
#        }),
#        ('Важные даты', {
#            'fields': (
#                ('created_at',)
#            ),
#        }),
#    )
#    filter_horizontal = ('users',)
#    readonly_fields = ('created_at',)
