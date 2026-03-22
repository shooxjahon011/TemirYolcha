from django.conf import settings
from django.conf.urls.static import static
from django.urls import path
from django.views.generic import TemplateView
from . import views

urlpatterns = [
    # Kirish va chiqish
    path('', views.login_view, name='Login'),
    path('logout/', views.logout_view, name='logout'),
    path('verify-code/', views.verify_code_view, name='verify_code'),
    path('signup/', views.signup, name='Sign Up'),
    path('boss-registration/', views.boss_registration, name='boss_registration'),
    path('get-guruhlar/', views.get_guruhlar, name='get_guruhlar'), # AJAX uchun
    path('transfer-train/<int:train_id>/', views.transfer_train_data, name='transfer_train'),
    path('ajax/get-guruhlar/', views.get_guruhlar, name='ajax_get_guruhlar'),
    path('task-respond/<int:train_id>/<str:action>/', views.respond_to_train, name='respond_to_train'),
    path('malumot/', views.malumot_uzatish_view, name='malumot_uzatish_url'),
    path('api/acu-receiver/', views.handle_acu_data, name='acu_receiver'),
    path('transfer-train-api/<int:train_id>/', views.transfer_train_api, name='transfer_train_api'),
    path('ajax/get-guruhlar/', views.get_guruhlar_ajax, name='get_guruhlar_ajax'),

    # Tanlangan ishchining poezdini boshqa guruhga yuborish (API)
    path('transfer-train-api/<int:train_id>/', views.transfer_train_api, name='transfer_train_api'),

    # PWA va Servislar
    path('manifest.json', TemplateView.as_view(template_name='manifest.json', content_type='application/json')),
    path('sw.js', TemplateView.as_view(template_name='sw.js', content_type='application/javascript')),

    # Poyezdlar bilan ishlash (BOSS uchun)
    path('trains/', views.train_list_view, name='train_list'),
    path('sync-asu/', views.sync_from_kazakh_asu, name='sync_asu'),
    path('plustoworker/', views.plus_to_worker, name='plus_to_worker'),
    path('Poezdlar/', views.poezdlar, name='poezdlar'),
    path('vagon-muammo/<int:vagon_id>/', views.vagon_muammo_yozish, name='vagon_muammo'),
    # DIQQAT: HTML-da 'assign-train' ishlatilgan, shuning uchun shunday qolishi kerak
    path('assign-train/<int:train_id>/<int:worker_id>/', views.assign_train, name='assign_train'),
    path('check-vagon/<int:vagon_id>/', views.check_vagon_view, name='check_vagon'),
    path('holat/', views.poezd_holati, name='poezd_holati'),


    # Vagonlar detali oynasi (ID orqali o'tiladi)
# urls.py
    path('holat/vagonlar/<int:train_id>/', views.vagon_hisoboti, name='vagon_hisoboti'),
    path('train-finish/<int:train_id>/', views.poyezd_yakunlash_view, name='train_finish'),

    path('lookinglogs/', views.save_vagon_status, name='save_vagon_status'),

    # Poyezdga javob berish (ISHCHI uchun)
    # HTML-dagi '/task-respond/{{ task.id }}/accept/' yo'li uchun:
    path('task-respond/<int:task_id>/<str:action>/', views.task_respond, name='task_respond'),

    # Sahifalar
    path('second/', views.second_view, name='second_page'),
    path('bosspage/', views.boss, name='boss_page'),
    path('profile/', views.profile_view, name='Profil'),
    path('hisobot/', views.hisobot, name='Hisobotlar'),
    path('Baxtsizhodisalar/', views.baxtsiz_hodisa, name='Baxtsiz_hodisalar'),

    # Ishchilar va Lokatsiya
    path('active-workers/', views.active_workers_list, name='active_workers'),
    path('track-worker/<int:worker_id>/', views.track_worker, name='track_worker'),
    path('get-location/<int:worker_id>/', views.get_worker_location, name='get_worker_location'),
    path('toggle-work/', views.toggle_work, name='toggle_work'),
    path('update-location/', views.update_location, name='update_location'),

    # Maosh va Hisob-kitob
    path('okladmenu/', views.salary_menu_view, name='salary_menu'),
    path('tatil/', views.hisoblash_view, name='tatil_sahifasi'),
    path('Conculator/', views.salary_calc_view, name='salary_calc_high'),
    path('Kankulyator_Auto/', views.salary_calc_view1, name='salary_calc_low'),
    path('Kankulyator/', views.salary_calc_manual_view, name='salary_manual'),

    # Boss hisobotlari
    path('kunlik/', views.boss_reports, name='boss_reports'),
    path('boss/worker-report/<int:worker_id>/', views.add_report_for_worker, name='boss_worker_report'),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)