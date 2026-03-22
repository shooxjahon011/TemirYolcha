import PyPDF2
import docx
import csv
import openpyxl
from datetime import datetime, timezone
from django.db.models import  Sum
from django.http import HttpResponse,JsonResponse
from django.shortcuts import  redirect,render,get_object_or_404
from django.templatetags.static import static
from django.middleware.csrf import get_token
from django.views.decorators.csrf import csrf_exempt
from .models import  ChatMessage, WorkSchedule
from datetime import timedelta, date
from my_app.models import UserProfile, IshchiGuruh ,Otryad,UserLocation,LocationHistory,TrainChain,Vagon,TaskAssignment
import logging
from django.contrib.auth.models import User
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.db.models import Q
import json
import uuid
import math
from django.contrib import messages
from django.db import connections
from django.contrib.auth.hashers import make_password
from django.utils import timezone
logger = logging.getLogger(__name__)
def sync_from_kazakh_asu(request):  # request argumenti qo'shildi
    try:
        # 1. Qozog'iston bazasiga ulanish
        # Settings.py dagi 'kazakh_asu' blokidan foydalanadi
        with connections['kazakh_asu'].cursor() as cursor:

            # 2. ASU bazasidan ma'lumotlarni so'rash
            # DIQQAT: 'trains_table' o'rniga Qozog'iston bazasidagi haqiqiy jadval nomini yozing
            cursor.execute("SELECT id, train_no, data_json FROM trains_table")
            rows = cursor.fetchall()

            count = 0
            for row in rows:
                # 3. update_or_create — asu_id bo'yicha tekshiradi
                obj, created = TrainChain.objects.update_or_create(
                    asu_id=row[0],
                    defaults={
                        'train_number': row[1],
                        'asu_raw_data': row[2],
                    }
                )
                if created:
                    count += 1

        # Muvaffaqiyatli xabar yuborish
        messages.success(request, f"ASU bilan sinxronizatsiya yakunlandi! {count} ta yangi poezd qo'shildi.")

    except Exception as e:
        # Agar ulanishda yoki SQLda xato bo'lsa, xabarni ekranga chiqaradi
        messages.error(request, f"ASUga ulanishda xatolik: {str(e)}")

    # Amaliyot tugagach, poezdlar ro'yxati sahifasiga qaytarib yuboradi
    return redirect('train_list')
def boss_registration(request):
    # Otryad va Guruhlarni bazadan olish
    otryadlar = Otryad.objects.all()
    guruhlar = IshchiGuruh.objects.all()

    if request.method == "POST":
        f_name = request.POST.get('f_name', '').strip()
        l_name = request.POST.get('l_name', '').strip()
        u_login = request.POST.get('u_login')
        u_pass = request.POST.get('u_pass')
        u_phone = request.POST.get('phone')
        u_otryad_id = request.POST.get('otryad')
        u_guruh_id = request.POST.get('guruh')

        # Manzil ma'lumotlari
        viloyat = request.POST.get('viloyat')
        tuman = request.POST.get('tuman')
        mahalla = request.POST.get('mahalla')
        kocha = request.POST.get('kocha')
        uy = request.POST.get('uy')

        unique_tabel_raqami = f"BOSHLIQ-{u_login}-{uuid.uuid4().hex[:4].upper()}"

        try:
            UserProfile.objects.create(
                full_name=f"{f_name} {l_name}",
                login=u_login,
                password=make_password(u_pass),
                phone=u_phone,
                tabel_raqami=unique_tabel_raqami,
                otryad_id=u_otryad_id if u_otryad_id else None,
                guruh_id=u_guruh_id if u_guruh_id else None,
                viloyat=viloyat,
                shahar_tuman=tuman,
                mahalla=mahalla,
                kocha=kocha,
                uy_raqami=uy,
                is_boss=True,
                is_active=True
            )
            return redirect('/')
        except Exception as e:
            return HttpResponse(f"Xatolik yuz berdi: {e}")

    # Template-ga ma'lumotlarni yuborish
    context = {
        'otryadlar': otryadlar,
        'guruhlar': guruhlar
    }
    return render(request, 'boss_registration.html', context)
def baxtsiz_hodisa(request):
    user_login = request.session.get('user_login')
    if not user_login:
        return redirect('/')

    user = UserProfile.objects.filter(login=user_login).first()
    is_boss = getattr(user, 'is_boss', False)
    video_url = static('uzb.mp4')

    if request.method == "POST" and is_boss:
        fayl = request.FILES.get('admin_file')
        text_input = request.POST.get('text', '')
        final_content = text_input + "\n"

        if fayl:
            ext = fayl.name.split('.')[-1].lower()
            try:
                if ext == 'pdf':
                    reader = PyPDF2.PdfReader(fayl)
                    for page in reader.pages: final_content += page.extract_text() + "\n"
                elif ext in ['doc', 'docx']:
                    doc = docx.Document(fayl)
                    for para in doc.paragraphs: final_content += para.text + "\n"
                elif ext in ['xls', 'xlsx']:
                    wb = openpyxl.load_workbook(fayl, data_only=True)
                    for row in wb.active.iter_rows(values_only=True):
                        final_content += " | ".join([str(c) for c in row if c]) + "\n"
            except Exception as e:
                return HttpResponse(f"Fayl tahlilida xatolik: {e}")

        if final_content.strip():
            ChatMessage.objects.create(
                user=user,
                text=f"🔴 DIQQAT! BAXTSIZ HODISA XABARI:\nYubordi: {user.full_name or user.login}\n{final_content}"
            )
        return redirect('/Baxtsizhodisalar/')

    # Ma'lumotlarni yig'ish
    messages = ChatMessage.objects.filter(text__contains="DIQQAT! BAXTSIZ HODISA").order_by('-created_at')

    formatted_messages = []
    for m in messages:
        formatted_messages.append({
            'time': timezone.localtime(m.created_at).strftime('%H:%M | %d.%m.%Y'),
            'text': m.text.replace("🔴 DIQQAT! BAXTSIZ HODISA XABARI:", "").strip()
        })

    context = {
        'is_boss': is_boss,
        'video_url': video_url,
        'messages': formatted_messages,
    }
    return render(request, 'baxtsiz_hodisa.html', context)
def update_status(request):
    user_login = request.session.get('user_login')
    if user_login:
        UserProfile.objects.filter(login=user_login).update(last_seen=timezone.now())
        return HttpResponse("OK")
    return HttpResponse("Unauthorized", status=401)
def hisoblash_view(request):
    # GET ma'lumotlarini olish
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')
    user_okladi_str = request.GET.get('oklad')
    korsatkich_str = request.GET.get('korsatkich')

    context = {
        'video_url': static('uzb.mp4'),
        'start_date_str': start_date_str,
        'end_date_str': end_date_str,
        'user_okladi_str': user_okladi_str,
        'korsatkich_str': korsatkich_str,
        'result': None,
        'error': None
    }

    if start_date_str and end_date_str and user_okladi_str and korsatkich_str:
        try:
            start = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            end = datetime.strptime(end_date_str, "%Y-%m-%d").date()
            user_okladi = float(user_okladi_str)
            korsatkich = float(korsatkich_str)

            if start > end:
                context['error'] = "Sana noto'g'ri kiritildi!"
            else:
                count_yakshanba = 0
                total_days = 0
                current_date = start
                while current_date <= end:
                    total_days += 1
                    if current_date.weekday() == 6:
                        count_yakshanba += 1
                    current_date += timedelta(days=1)

                ish_kunlari = total_days - count_yakshanba
                foiz = 50 if korsatkich <= 20 else 75
                hisob_uchun_asos = user_okladi * (foiz / 100)
                KUNLIK_STAVKA = 100000
                ish_kunlari_uchun_haq = ish_kunlari * KUNLIK_STAVKA
                jami_summa = hisob_uchun_asos + ish_kunlari_uchun_haq

                context['result'] = {
                    'oklad': user_okladi,
                    'foiz': foiz,
                    'asos': hisob_uchun_asos,
                    'kunlar': ish_kunlari,
                    'kunlik_stavka': KUNLIK_STAVKA,
                    'kunlik_haq': ish_kunlari_uchun_haq,
                    'jami': jami_summa
                }
        except ValueError:
            context['error'] = "Ma'lumotlarni kiritishda xatolik!"

    return render(request, 'hisoblash.html', context)
def get_safe_razryad(user):
    try:
        if not user or not user.razryad:
            return 0
        r_str = str(user.razryad).strip()
        if "/" in r_str:
            num, den = r_str.split("/")
            return float(num) / float(den)
        return float(r_str)
    except (ValueError, TypeError, ZeroDivisionError):
        return 0
def salary_menu_view(request):
    user_login = request.session.get('user_login')
    if not user_login:
        return redirect('/')

    user = UserProfile.objects.filter(login=user_login).first()
    if not user:
        return redirect('/')

    # Razryadni tekshirish logikasi
    # get_safe_razryad funksiyasi mavjud deb hisoblaymiz
    current_razryad = get_safe_razryad(user)

    if current_razryad >= (5 / 3):
        auto_url = "/Conculator/"
    else:
        auto_url = "/Kankulyator_Auto/"

    context = {
        'user': user,
        'auto_url': auto_url,
        'video_url': static('uzb.mp4'),
    }
    return render(request, 'salary_menu.html', context)
def common_calculator_logic(request, bonus_rate, check_type):
    user_login = request.session.get('user_login')
    if not user_login:
        return redirect('/')

    # Formadan kelayotgan ma'lumotlar
    salary = request.GET.get('salary')
    norma_soat = request.GET.get('norma_soat')
    ishlangan_soat = request.GET.get('ishlangan_soat')
    tungi_soat = request.GET.get('tungi_soat', '0')
    bayram_soati = request.GET.get('bayram_soati', '0')

    context = {
        'salary': salary,
        'norma_soat': norma_soat,
        'ishlangan_soat': ishlangan_soat,
        'tungi_soat': tungi_soat,
        'bayram_soati': bayram_soati,
        'video_url': static('uzb.mp4'),
        'netto': None,
        'error': None
    }

    if salary and norma_soat and ishlangan_soat:
        try:
            s = float(salary)
            n_s = float(norma_soat)
            i_s = float(ishlangan_soat)
            t_s = float(tungi_soat or 0)
            b_s = float(bayram_soati or 0)

            # Bir soatlik ish haqi
            m = s / n_s

            # Brutto hisoblash formulasi
            # (m * i_s) -> oylik
            # (m * i_s * bonus_rate) -> bonus (50% yoki 75%)
            # (t_s * m * 0.5) -> tungi soat ustamasi
            # ((490000 / n_s) * i_s) -> ovqatlanish puli (misol)
            # (b_s * m) -> bayram soati uchun 100% ustama
            brutto = (m * i_s) + (m * i_s * bonus_rate) + (t_s * m * 0.5) + ((490000 / n_s) * i_s) + (b_s * m)

            # Soliqlarni chegirish (13.1%)
            soliq = brutto * 0.131
            context['netto'] = brutto - soliq

        except (ValueError, ZeroDivisionError):
            context['error'] = "Ma'lumotlarni kiritishda xatolik yuz berdi!"

    return render(request, 'calculator_base.html', context)
def salary_calc_manual_view(request):
    user_login = request.session.get('user_login')
    if not user_login:
        return redirect('/')

    # Formadan kelayotgan ma'lumotlar
    salary = request.GET.get('salary')
    norma_soat = request.GET.get('norma_soat')
    ishlangan_soat = request.GET.get('ishlangan_soat')
    bonus_percent = request.GET.get('bonus_percent')
    tungi_soat = request.GET.get('tungi_soat', '0')
    bayram_soati = request.GET.get('bayram_soati', '0')

    context = {
        'salary': salary,
        'norma_soat': norma_soat,
        'ishlangan_soat': ishlangan_soat,
        'bonus_percent': bonus_percent,
        'tungi_soat': tungi_soat,
        'bayram_soati': bayram_soati,
        'video_url': static('uzb.mp4'),
        'netto': None,
        'error': None
    }

    if salary and norma_soat and ishlangan_soat and bonus_percent:
        try:
            s = float(salary)
            n = float(norma_soat)
            i = float(ishlangan_soat)
            bp = float(bonus_percent) / 100
            ts = float(tungi_soat or 0)
            bs = float(bayram_soati or 0)

            # Bir soatlik stavka
            m = s / n

            # Brutto: Oylik + Mukofot + Tungi + Ovqatlanish + Bayram
            brutto = (m * i) + (m * i * bp) + (ts * m * 0.5) + ((490000 / n) * i) + (bs * m)

            # 13.1% Soliqni chegirish
            context['netto'] = brutto - (brutto * 0.131)

        except (ValueError, ZeroDivisionError):
            context['error'] = "Ma'lumotlarda xatolik yuz berdi!"

    return render(request, 'calculator_manual.html', context)
def render_page(request, rate, s, n, i, ts, bs, netto=None, error=None, is_manual=False, bonus_percent=""):
    # Dinamik sarlavha va ranglarni aniqlash
    title = "QO'LDA KIRITISH" if is_manual else f"{int(rate * 100)}% KALKULYATOR"
    color = "#ff9d00" if is_manual else "#00f2ff"

    context = {
        'title': title,
        'color': color,
        'is_manual': is_manual,
        'salary': s,
        'norma_soat': n,
        'ishlangan_soat': i,
        'bonus_percent': bonus_percent,
        'tungi_soat': ts,
        'bayram_soati': bs,
        'netto': netto,
        'error': error,
        'video_url': static('uzb.mp4'),  # Video fon uchun
    }

    return render(request, 'calculator_template.html', context)
def salary_calc_view(request):
    return common_calculator_logic(request, 0.20, "high")
def salary_calc_view1(request):
    return common_calculator_logic(request, 0.40, "low")
def boss_reports(request):
    user_login = request.session.get('user_login')
    if not user_login:
        return redirect('/login/')

    # Boss profilini tekshirish
    boss = UserProfile.objects.filter(login=user_login).first()
    if not boss or not boss.is_boss:
        return redirect('/second/')

    # Bossning otryadidagi ishchilarni filtrlash
    workers = UserProfile.objects.filter(otryad=boss.otryad, is_boss=False)

    context = {
        'boss': boss,
        'workers': workers,
        'video_url': static('uzb.mp4'),
    }

    return render(request, 'boss_reports.html', context)
def add_report_for_worker(request, worker_id):
    # Foydalanuvchi va Boss tekshiruvi
    user_login = request.session.get('user_login')
    if not user_login:
        return redirect('/login/')

    boss = UserProfile.objects.filter(login=user_login).first()
    if not boss or not boss.is_boss:
        return redirect('/second/')

    # Ishchini topamiz
    worker = get_object_or_404(UserProfile, id=worker_id)

    if request.method == "POST":
        try:
            # Formadan ma'lumotlarni olish
            WorkSchedule.objects.create(
                user=worker,
                date=request.POST.get('sana'),
                oklad=request.POST.get('oklad'),
                norma_soati=request.POST.get('norma'),
                ishlagan_soati=request.POST.get('ishlagan'),
                tungi_soati=request.POST.get('tungi', 0) or 0,
                bayram_soati=request.POST.get('bayram', 0) or 0
            )
            return redirect(f'/boss/worker-report/{worker.id}/')
        except Exception as e:
            # Xatolikni template orqali ko'rsatish tavsiya etiladi
            return render(request, 'add_report.html', {'worker': worker, 'error': str(e)})

    context = {
        'worker': worker,
        'today_date': timezone.now().strftime('%Y-%m-%d'),
        'video_url': static('uzb.mp4'),
    }
    return render(request, 'add_report.html', context)
def assign_worker_to_train(request, train_id, worker_id):
    # 1. Boss ekanligini tekshirish (Sessiyadan)
    user_login = request.session.get('user_login')
    boss = UserProfile.objects.filter(login=user_login).first()

    if not boss or not boss.is_boss:
        messages.error(request, "Ushbu amal uchun sizda huquq yo'q!")
        return redirect('/login/')

    # 2. Poyezd va Ishchi profilini olish
    train = get_object_or_404(TrainChain, id=train_id)
    worker_profile = get_object_or_404(UserProfile, id=worker_id)

    # 3. Ishchining Django User obyektini login orqali topish (Katta-kichik harfga e'tibor berib)
    worker_user = User.objects.filter(username__iexact=worker_profile.login).first()

    if not worker_user:
        messages.error(request, f"Xatolik: {worker_profile.login} logini tizimda (User modelida) topilmadi!")
        return redirect('/plustoworker/')

    # 4. --- ASOSIY CHEKLOV ---
    # Ishchida allaqachon kutilayotgan (pending) yoki tasdiqlangan (confirmed) poyezd bormi?
    already_has_train = TrainChain.objects.filter(
        assigned_worker=worker_user,
        assignment_status__in=['pending', 'confirmed']
    ).exists()

    if already_has_train:
        messages.warning(request,
                         f"{worker_profile.full_name}da allaqachon poyezd bor! Faqat 1 ta poyezd biriktirish mumkin.")
        return redirect('/plustoworker/')

    try:
        # 5. POYEZDNI BIRIKTIRISH
        train.assigned_worker = worker_user
        train.assignment_status = 'pending'
        train.save()

        # Muvaffaqiyatli xabar
        messages.success(request,
                         f"№{train.train_number} poyezdi {worker_profile.full_name}ga yuborildi. Tasdiqlash kutilmoqda.")

    except Exception as e:
        messages.error(request, f"Saqlashda xatolik yuz berdi: {e}")

    return redirect('/plustoworker/')
def assign_panel_view(request):
    # 1. Hozirda band bo'lgan ishchilarning IDlarini olamiz
    busy_workers_ids = TrainChain.objects.filter(
        assignment_status__in=['pending', 'confirmed']
    ).values_list('assigned_worker_id', flat=True)

    # 2. Faqat band bo'lmagan (bo'sh) ishchilarni filtrlaymiz
    # active_locations - bu ishga kelgan ishchilar
    free_locations = UserLocation.objects.filter(
        user__is_active=True,
        user__is_boss=False
    ).exclude(user_id__in=busy_workers_ids)  # Bandlarini olib tashlaymiz

    trains = TrainChain.objects.all().order_by('-id')

    context = {
        'trains': trains,
        'active_locations': free_locations,  # Endi bu yerda faqat bo'sh ishchilar bor
        'display_name': request.session.get('full_name', 'Admin'),
    }
    return render(request, 'boss_assign_panel.html', context)
def task_respond(request, task_id, action):
    # 1. Sessiyadan loginni olamiz
    user_login = request.session.get('user_login')

    # 2. Topshiriqni bazadan qidiramiz
    task = get_object_or_404(TrainChain, id=task_id)

    # 3. XATONI TUZATISH:
    # assigned_worker bu 'User' obyekti. Unda .login emas, .username bo'ladi.
    if not user_login or task.assigned_worker.username != user_login:
        # Agar topshiriq bu ishchiga tegishli bo'lmasa, ruxsat bermaymiz
        return HttpResponse("Xatolik: Bu topshiriq sizga tegishli emas!", status=403)

    if action == 'accept':
        # Qabul qilinsa: statusni confirmed qilamiz va ishchini 'is_working' holatiga o'tkazamiz
        task.assignment_status = 'confirmed'
        task.save()

        # Ishchi profilini topib, statusini band (is_working=True) qilamiz
        profile = UserProfile.objects.filter(login=user_login).first()
        if profile:
            profile.is_working = True
            profile.save()

    elif action == 'reject':
        # Rad etilsa: statusni qaytadan 'free' qilamiz va ishchini bo'shatamiz
        task.assignment_status = 'free'
        task.assigned_worker = None
        task.save()

    # Hammasi tugagach, yana bosh menyuga qaytaramiz
    return redirect('/second/')
def assign_train(request, train_id, worker_id):
    from django.contrib import messages

    # 1. Poyezd va Ishchini bazadan qidiramiz
    train = get_object_or_404(TrainChain, id=train_id)
    worker = get_object_or_404(UserProfile, id=worker_id)

    # 2. To'g'ridan-to'g'ri UserProfile obyektini biriktiramiz
    try:
        train.assigned_worker = worker
        train.assignment_status = 'pending'
        train.save()

        # 3. TaskAssignment yaratish (Vagonlar chiqishi uchun kerak bo'lishi mumkin)
        TaskAssignment.objects.get_or_create(
            worker=worker,
            train_index=train.train_number,
            defaults={'status': 'pending'}
        )

        messages.success(request, f"№{train.train_number} poyezdi {worker.full_name}ga biriktirildi.")
    except Exception as e:
        messages.error(request, f"Xatolik yuz berdi: {e}")

    return redirect('/plustoworker/')
def second_view(request):
    user_login = request.session.get('user_login')
    if not user_login:
        return redirect('/')

    # 1. Ishchi profilini topamiz
    profile = UserProfile.objects.filter(login=user_login).first()
    if not profile:
        return redirect('/')

    # Boss bo'lsa profiliga qaytarish
    if getattr(profile, 'is_boss', False):
        return redirect('/bosspage/')

    # 2. Aynan shu ishchiga biriktirilgan va kutilayotgan (pending) poyezdlar
    # DIQQAT: assigned_worker endi UserProfile'ga bog'langan deb hisoblaymiz
    tasks = TrainChain.objects.filter(
        assigned_worker=profile,
        assignment_status='pending'
    ).order_by('-id')

    # 3. Hozirda tasdiqlangan va ustida ishlanayotgan poyezd
    active_task = TrainChain.objects.filter(
        assigned_worker=profile,
        assignment_status='confirmed'
    ).first()

    context = {
        'user': profile,
        'display_name': profile.full_name or profile.login,
        'avatar_url': profile.image.url if profile.image else static('default.png'),
        'is_working': profile.is_working,
        'tasks': tasks,  # Modalda chiqadigan ro'yxat
        'active_task': active_task,  # Sahifaning yuqorisida turadigan kartochka
        'video_url': static('uzb.mp4'),
        'csrf_token': get_token(request),
        'btn_text': "Ishni tugatdim" if profile.is_working else "Men ishga keldim",
        'btn_class': "btn-working" if profile.is_working else "btn-idle",
    }
    return render(request, 'main_menu.html', context)
def respond_to_train(request, train_id, action):
    # Bu funksiya modal ichidagi tugmalar uchun
    train = get_object_or_404(TrainChain, id=train_id)

    if action == 'accept':
        train.assignment_status = 'confirmed'
        messages.success(request, f"№{train.train_number} poyezdi qabul qilindi!")
        # Ishchini band holatiga o'tkazish
        if train.assigned_worker:
            train.assigned_worker.is_working = True
            train.assigned_worker.save()

    elif action == 'reject':
        train.assignment_status = 'free'
        train.assigned_worker = None  # Poyezdni bo'shatish
        messages.warning(request, "Poyezdni rad etdingiz.")

    train.save()
    return redirect('/second/')
def profile_view(request):
    user_login = request.session.get('user_login')
    if not user_login:
        return redirect('/')

    user = UserProfile.objects.filter(login=user_login).first()
    if not user:
        return redirect('/')

    # Ma'lumotlarni yangilash
    if request.method == "POST":
        new_name = request.POST.get('display_name')
        new_pic = request.FILES.get('profile_pic')

        if new_name:
            user.login = new_name
        if new_pic:
            user.image = new_pic

        user.save()
        request.session['user_login'] = user.login
        return redirect('/profile/')

    context = {
        'user': user,
        'avatar_url': user.image.url if user.image else static('default_avatar.png'),
        'video_url': static('uzb.mp4'),
        'user_razryad': getattr(user, 'razryad', 'Kiritilmagan'),
    }

    return render(request, 'profile.html', context)
def logout_view(request):
    request.session.flush()
    return redirect('../') # Login sahifasiga qaytarish
def delete_message(request, msg_id):
    if request.method == "POST":
        msg = ChatMessage.objects.filter(id=msg_id).first()
        # Faqat o'z xabarini yoki admin o'chira olishi uchun:
        user_login = request.session.get('user_login')
        if msg and msg.user.login == user_login:
            msg.delete()
            return HttpResponse("OK")
    return HttpResponse("Xato", status=400)
def login_view(request):
    error_message = ""

    if request.method == "POST":
        u = request.POST.get('u_name', '').strip()
        p = request.POST.get('p_val', '').strip()

        # Maxsus kirish kodi
        if u == "1" and p == "1":
            return redirect('/boss-registration/')

        user = UserProfile.objects.filter(login__iexact=u).first()

        if not user:
            error_message = f'"{u}" logini topilmadi!'
        elif user.password != p:
            error_message = "Parol noto'g'ri!"
        else:
            request.session['user_login'] = user.login
            return redirect('/second/')

    context = {
        'error_message': error_message,
        'video_url': static('uzb.mp4'),
    }
    return render(request, 'login.html', context)
def signup(request):
    if request.method == "POST":
        u = request.POST.get('u_name')
        p = request.POST.get('p_val')
        tel = request.POST.get('tel_val')
        tabel = request.POST.get('t_raqam')
        fname = request.POST.get('full_name')
        raz_val = request.POST.get('razryad')
        guruh_id = request.POST.get('guruh_id')
        otryad_id = request.POST.get('otryad_id')

        tariflar = {"5/3": 5336929, "5/2": 4800000, "4/3": 4100000}
        oklad_val = tariflar.get(raz_val, 0)

        if UserProfile.objects.filter(login=u).exists():
            return render(request, 'signup.html', {'error': 'Bu login band!', 'otryadlar': Otryad.objects.all()})

        if all([u, p, tel, guruh_id, otryad_id]):
            try:
                otryad_obj = Otryad.objects.get(id=int(otryad_id))
                guruh_obj = IshchiGuruh.objects.get(id=int(guruh_id))

                yangi_user = UserProfile(
                    login=u, password=p, phone=tel,
                    tabel_raqami=tabel, full_name=fname,
                    razryad=raz_val, oklad=oklad_val,
                    is_active=False,
                    otryad=otryad_obj,
                    guruh=guruh_obj
                )
                yangi_user.save()
                return redirect(f'/verify-code/?login={u}')
            except Exception as e:
                return render(request, 'signup.html', {'error': f'Xatolik: {e}', 'otryadlar': Otryad.objects.all()})
        else:
            return render(request, 'signup.html',
                          {'error': 'Barcha maydonlarni to\'ldiring!', 'otryadlar': Otryad.objects.all()})

    # GET so'rovi uchun ma'lumotlar
    otryadlar = Otryad.objects.all()
    guruhlar = IshchiGuruh.objects.all()

    guruhlar_dict = {}
    for g in guruhlar:
        if g.otryad_id not in guruhlar_dict:
            guruhlar_dict[g.otryad_id] = []
        guruhlar_dict[g.otryad_id].append({'id': g.id, 'nomi': g.nomi})

    context = {
        'otryadlar': otryadlar,
        'guruhlar_json': json.dumps(guruhlar_dict),
        'video_url': static('uzb.mp4'),
    }
    return render(request, 'signup.html', context)
def verify_code_view(request):
    # GET yoki POST orqali kelgan loginni olish
    login_val = request.GET.get('login') or request.POST.get('login')
    user = UserProfile.objects.filter(login=login_val).first()

    if not user:
        return redirect('/')

    if request.method == "POST":
        entered_code = request.POST.get('activation_code')

        if user.activation_code == entered_code:
            user.is_active = True
            user.save()
            request.session['user_login'] = user.login
            return redirect('/second/')
        else:
            # Xato kod kiritilganda sahifani xato xabari bilan qaytaramiz
            return render(request, 'verify_code.html', {
                'error': "Xato kod kiritildi!",
                'login_val': login_val,
                'video_url': static('uzb.mp4')
            })

    context = {
        'login_val': login_val,
        'video_url': static('uzb.mp4'),
    }
    return render(request, 'verify_code.html', context)
def hisobot(request):
    user_login = request.session.get('user_login')
    if not user_login:
        return redirect('/')

    current_user = UserProfile.objects.filter(login=user_login).first()
    if not current_user:
        return redirect('/')

    # Jadval ma'lumotlarini olish
    jadval_malumotlari = WorkSchedule.objects.filter(user=current_user).order_by('-date')

    # Jami yig'indilarni hisoblash
    jami = jadval_malumotlari.aggregate(
        t_ish=Sum('ishlagan_soati'),
        t_tungi=Sum('tungi_soati'),
        t_bayram=Sum('bayram_soati')
    )

    # Oxirgi kiritilgan norma va okladni olish (jami qatori uchun)
    last_entry = jadval_malumotlari.first()

    context = {
        'current_user': current_user,
        'jadval': jadval_malumotlari,
        'jami': jami,
        'last_entry': last_entry,
        'video_url': static('uzb.mp4'),
    }

    return render(request, 'hisobot.html', context)
def boss(request):
    user_login = request.session.get('user_login')
    if not user_login:
        return redirect('/login/')

    user = UserProfile.objects.filter(login=user_login).first()

    # Boss ekanligini tekshirish
    if not user or not user.is_boss:
        return redirect('/second/')

    # Aktiv ishchilar sonini hisoblash (Jonli kuzatuv uchun)
    active_workers_count = UserLocation.objects.filter(is_active=True).count()

    context = {
        'display_name': user.full_name or user.login,
        'avatar_url': user.image.url if user.image else static('default_avatar.png'),
        'guruh_nomi': user.otryad.nomi if user.otryad else "Bo'lim tayinlanmagan",
        'active_workers_count': active_workers_count,
        'video_url': static('uzb.mp4'),
    }
    return render(request, 'boss_panel.html', context)
def active_workers_list(request):
    # 1. Login tekshiruvi
    user_login = request.session.get('user_login')
    if not user_login:
        return redirect('/login/')

    # 2. Boss profili va uning izolyatsiya chegaralarini olish
    boss = UserProfile.objects.filter(login=user_login).first()
    if not boss or not boss.is_boss:
        return redirect('/second/')

    # 3. IZOLYATSIYA FILTRI:
    # Faqat bossning otryadi va guruhidagi, hamda aktiv bo'lgan ishchilarni olamiz
    active_locations = UserLocation.objects.filter(
        is_active=True,
        user__otryad=boss.otryad,  # Bossning otryadi bilan bir xil bo'lishi shart
        user__guruh=boss.guruh      # Bossning guruhi bilan bir xil bo'lishi shart
    ).select_related('user')

    context = {
        'active_locations': active_locations,
        'count': active_locations.count(),
        'default_avatar': static('default_avatar.png'),
    }
    return render(request, 'active_workers.html', context)
def track_worker(request, worker_id):
    user_login = request.session.get('user_login')
    if not user_login:
        return redirect('/login/')

    # Ishchini bazadan olish
    worker = get_object_or_404(UserProfile, id=worker_id)

    # Boshlang'ich kordinatalarni olish
    last_loc = UserLocation.objects.filter(user=worker).first()

    context = {
        'worker': worker,
        'display_name': worker.full_name or worker.login,
        'start_lat': last_loc.latitude if last_loc else 41.3111,
        'start_lng': last_loc.longitude if last_loc else 69.2797,
    }
    return render(request, 'track_worker.html', context)
def get_worker_location(request, worker_id):
    worker = get_object_or_404(UserProfile, id=worker_id)
    try:
        loc = UserLocation.objects.get(user=worker)
        return JsonResponse({
            'lat': loc.latitude,
            'lng': loc.longitude,
            'is_active': loc.is_active
        })
    except UserLocation.DoesNotExist:
        return JsonResponse({'error': 'Not found'}, status=404)
@csrf_exempt
def toggle_work(request):
    if request.method == "POST":
        user_login = request.session.get('user_login')

        if not user_login:
            return JsonResponse({"status": "error", "message": "Foydalanuvchi topilmadi"}, status=403)

        user = get_object_or_404(UserProfile, login=user_login)
        action = request.POST.get('action')

        # 1. UserProfile modelidagi is_working ni yangilash
        if action == 'start':
            user.is_working = True
            user.work_start_time = timezone.now()
            logger.info(f"User {user.login} started work.")

        elif action == 'stop':
            user.is_working = False
            logger.info(f"User {user.login} stopped work.")

        user.save()

        # 2. UserLocation modelidagi is_active ni yangilash
        # get_or_create xatolik bermasligi uchun standart qiymatlar beramiz
        user_loc, created = UserLocation.objects.get_or_create(
            user=user,
            defaults={
                'latitude': 0.0,  # Standart qiymat
                'longitude': 0.0,  # Standart qiymat
                'is_active': False
            }
        )

        user_loc.is_active = (action == 'start')
        # Agar 'start' bo'lsa va latitude 0 bo'lsa, uni haqiqiy GPS bilan
        # update_location funksiyasida yangilashni kuting.
        user_loc.save()

        return JsonResponse({"status": "success", "is_working": user.is_working})

    return JsonResponse({"status": "error", "message": "Faqat POST so'rovi qabul qilinadi"}, status=405)@csrf_exempt  # GPS so'rovlari API orqali kelgani uchun CSRF tekshiruvini o'chiramiz
def update_location(request):
    """
    Ishchining joriy joylashuvini yangilaydi
    """
    if request.method == "POST":
        # Foydalanuvchini sessiyadan olish
        user_login = request.session.get('user_login')

        if not user_login:
            return JsonResponse({"status": "error", "message": "Foydalanuvchi topilmadi"}, status=403)

        # Foydalanuvchi obyektini bazadan olish
        user = get_object_or_404(UserProfile, login=user_login)

        # Koordinatalarni olish
        lat = request.POST.get('lat')
        lng = request.POST.get('lng')

        if not lat or not lng:
            return JsonResponse({"status": "error", "message": "Koordinatalar yo'q"}, status=400)

        # 1. Joriy joylashuvni yangilash (yoki yaratish)
        user_loc, created = UserLocation.objects.get_or_create(user=user)
        user_loc.latitude = lat
        user_loc.longitude = lng
        user_loc.last_updated = timezone.now()
        user_loc.is_active = True  # GPS ma'lumot kelayotgan bo'lsa, demak ishda
        user_loc.save()

        # 2. Tarixga yozish (LocationHistory modelida tarix bo'lsa)
        LocationHistory.objects.create(
            user=user,
            latitude=lat,
            longitude=lng
        )

        logger.info(f"Updated location for {user.login}: {lat}, {lng}")

        return JsonResponse({"status": "success", "message": "Joylashuv yangilandi"})

    return JsonResponse({"status": "error", "message": "Faqat POST so'rovi qabul qilinadi"}, status=405)
def respond_to_assignment(request, train_id, response):
    train = get_object_or_404(TrainChain, id=train_id, assigned_worker=request.user)

    if response == 'accept':
        train.assignment_status = 'confirmed'
        messages.success(request, "Poezdni qabul qildingiz. Ishga tushirildi.")
    else:
        train.assigned_worker = None
        train.assignment_status = 'free'
        messages.info(request, "Biriktirish rad etildi.")

    train.save()
    return redirect('worker_dashboard')
def worker_response(request, train_id, action):
    train = get_object_or_404(TrainChain, id=train_id)

    if action == 'accept':
        train.status = 'confirmed'  # BIRIKTIRILGAN
        messages.success(request, "Poyezdni qabul qildingiz!")
    elif action == 'reject':
        train.status = 'free'  # BO'SH (Rad etildi)
        train.worker = None  # Ishchini o'chiramiz
        messages.warning(request, "Poyezdni rad etdingiz!")

    train.save()
    return redirect('/second/')


def plus_to_worker(request):
    # 1. Sessiyadan foydalanuvchini tekshirish
    user_login = request.session.get('user_login')
    boss = UserProfile.objects.filter(login=user_login).first()

    if not boss or not boss.is_boss:
        return redirect('/login/')

    # 2. Bossning guruhidagi ishchilar ID ro'yxatini olish
    # Bu ro'yxat poyezdlarni va ishchilar holatini filtrlash uchun kerak
    my_worker_ids = UserProfile.objects.filter(
        guruh=boss.guruh,
        is_boss=False
    ).values_list('id', flat=True)

    # 3. POYEZDLARNI FILTRLASH
    # MUHIM: TrainChain modelida 'guruh' fieldi yo'qligi sababli hozircha
    # faqat 'otryad' bo'yicha filtrlaymiz (FieldError oldini olish uchun)
    trains = TrainChain.objects.filter(
        otryad=boss.otryad
    ).filter(
        # Faqat bo'sh poyezdlar YOKI shu bossning ishchilariga biriktirilgan poyezdlar ko'rinsin
        Q(assigned_worker__isnull=True) |
        Q(assignment_status='free') |
        Q(assigned_worker_id__in=my_worker_ids)
    ).order_by('-received_at').distinct()

    # 4. ISHCHILARNING LOKATSIYASI VA BANDLIK HOLATI
    # Bossning guruhidagi ishchilar lokatsiyasini olamiz
    active_locations = UserLocation.objects.filter(user_id__in=my_worker_ids).select_related('user')

    # Hozirda poyezd bilan band bo'lgan ishchilar ID ro'yxati
    busy_worker_ids = TrainChain.objects.filter(
        assigned_worker_id__in=my_worker_ids,
        assignment_status__in=['pending', 'confirmed']
    ).values_list('assigned_worker_id', flat=True)

    # Har bir lokatsiya obyektiga vaqtinchalik 'is_busy' flagini qo'shamiz
    for loc in active_locations:
        loc.is_busy = loc.user.id in busy_worker_ids

    # 5. Kontekstni shakllantirish
    context = {
        'trains': trains,
        'active_locations': active_locations,
        'boss': boss,
        'display_name': boss.full_name or boss.login,
        'video_url': '/static/uzb.mp4',  # Video mavjudligiga ishonch hosil qiling
    }

    return render(request, 'plus_to_worker.html', context)
def finish_train_work(request, train_id):
    """
    Ishchi tomonidan poyezd tekshiruvi yakunlanganda chaqiriladi.
    Statusni 'completed'ga o'zgartiradi va vagonlarni yopadi.
    """
    # 1. Poyezdni bazadan qidiramiz
    train = get_object_or_404(TrainChain, id=train_id)

    # 2. Xavfsizlik tekshiruvi: Faqat biriktirilgan ishchi tugata olishi kerak
    if train.assigned_worker != request.user:
        messages.error(request, "Sizga biriktirilmagan poyezdni yakunlay olmaysiz!")
        return redirect('/second/')

    # 3. Poyezd statusini yangilaymiz
    # MUHIM: assigned_worker ni None qilmang, aks holda Boss panelida ism yo'qoladi!
    train.assignment_status = 'completed'
    train.is_processed = True

    # 4. Ushbu poyezdga tegishli barcha vagonlarni avtomatik 'tekshirilgan' deb belgilash
    # (Agar ishchi biron vagonni unutib qoldirgan bo'lsa ham, umumiy poyezd yopilishi kerak)
    vagonlar = Vagon.objects.filter(train=train)
    for vagon in vagonlar:
        if not vagon.is_checked:
            vagon.is_checked = True
            vagon.save()

    # 5. Ma'lumotlarni saqlaymiz
    train.save()

    # 6. Muvaffaqiyatli xabar va yo'naltirish
    messages.success(request,
                     f"№{train.train_number} poyezdi va uning {vagonlar.count()} ta vagoni tekshiruvi to'liq yakunlandi.")

    return redirect('/second/')
def poezdlar(request):
    # 1. Sessiyadan foydalanuvchini aniqlash
    user_login = request.session.get('user_login')
    if not user_login:
        return redirect('login')  # Login qilmagan bo'lsa yo'naltirish

    profile = UserProfile.objects.filter(login=user_login).first()

    # 2. Ishchiga biriktirilgan hozirgi AKTIV vazifani topish
    # 'confirmed' statusli poyezdni qidiramiz
    active_task = TrainChain.objects.filter(
        assigned_worker=profile,
        assignment_status='confirmed'
    ).first()

    # --- POST SO'ROVI (Ma'lumotlarni saqlash) ---
    if request.method == "POST":
        if active_task:
            # Formadan kelgan barcha vagon ma'lumotlarini aylanamiz
            for key, value in request.POST.items():
                # key format: 'vagon_12_status'
                if key.startswith('vagon_') and key.endswith('_status'):
                    vagon_id = key.split('_')[1]  # ID ni ajratib olish
                    status = value  # 'ok' yoki 'problem'
                    comment = request.POST.get(f'vagon_{vagon_id}_comment', '')

                    # Vagonni bazadan topish va yangilash
                    vagon = Vagon.objects.filter(id=vagon_id).first()
                    if vagon:
                        vagon.is_checked = True
                        vagon.has_issue = (status == 'problem')
                        vagon.comment = comment
                        vagon.save()

            # Barcha vagonlar saqlangach, poyezd statusini 'completed' qilamiz
            active_task.assignment_status = 'completed'
            active_task.save()

            messages.success(request, "Hisobot muvaffaqiyatli yuborildi!")
            return redirect('/second/')  # Asosiy menyuga qaytish

    # --- GET SO'ROVI (Sahifani ko'rsatish) ---
    wagons = []
    if active_task:
        # Vagonlarni tartib raqami bo'yicha olamiz
        # Agar vagonlar to'g'ridan-to'g'ri 'train'ga bog'langan bo'lsa:
        wagons = Vagon.objects.filter(train=active_task).order_by('tartib_raqam')

        # Agar 'train' orqali chiqmasa, 'task' orqali tekshirib ko'ring:
        if not wagons.exists():
            task_obj = TaskAssignment.objects.filter(train_index=active_task).first()
            if task_obj:
                wagons = Vagon.objects.filter(task=task_obj).order_by('tartib_raqam')

    context = {
        'active_task': active_task,
        'wagons': wagons,
        'profile': profile
    }

    return render(request, 'poezd_details.html', context)
def save_vagon_status(request):
    if request.method == "POST":
        # 1. Sessiyadan joriy foydalanuvchini aniqlash
        user_login = request.session.get('user_login')
        profile = UserProfile.objects.filter(login=user_login).first()

        if not profile:
            return redirect('/login/')  # Agar login qilmagan bo'lsa

        # 2. Ishchiga biriktirilgan va tasdiqlangan (active) vazifani topish
        # assignment_status modelda 'confirmed' yoki 'process' bo'lishi mumkin
        task = TrainChain.objects.filter(
            assigned_worker=profile,
            assignment_status='confirmed'
        ).first()

        if task:
            # 3. POST so'rovidan kelgan barcha vagon ma'lumotlarini aylanamiz
            # HTMLda name="vagon_{{ wagon.id }}_status" ko'rinishida yuborilgan
            for key, value in request.POST.items():
                if key.startswith('vagon_') and key.endswith('_status'):
                    vagon_id = key.split('_')[1]
                    status = value  # 'ok' yoki 'problem'

                    # Izohni (comment) olish
                    comment_key = f'vagon_{vagon_id}_comment'
                    comment = request.POST.get(comment_key, '')

                    # 4. Vagon modelini topish va yangilash
                    vagon = Vagon.objects.filter(id=vagon_id).first()
                    if vagon:
                        vagon.is_checked = True
                        vagon.has_issue = (status == 'problem')
                        vagon.comment = comment
                        vagon.save()

            # 5. Butun poyezd tekshiruvi tugagach, vazifa statusini o'zgartiramiz
            # Bu vazifa endi Boss panelida (/holat/ da) ko'rinadigan bo'ladi
            task.assignment_status = 'completed'
            task.save()

        # 6. Muvaffaqiyatli yakunlangach, menyuga qaytarish
        return redirect('/second/')

    # Agar POST bo'lmasa, shunchaki qaytarib yuborish
    return redirect('/second/')
def poyezd_yakunlash_view(request, train_id):
    """ Poyezd ishini yakunlab yuborish """
    train = get_object_or_404(TrainChain, id=train_id)
    train.assignment_status = 'completed'
    train.save()
    messages.success(request, "Poyezd muvaffaqiyatli yuborildi!")
    return redirect('/second/')
def poezd_holati(request):
    """
    BOSS uchun: Faqat o'z guruhidagi ISHCHILAR tomonidan
    tugatilgan (completed) vazifalar ro'yxatini ko'rsatish.
    """
    # 1. Sessiyadan foydalanuvchini olish
    user_login = request.session.get('user_login')
    profile = UserProfile.objects.filter(login=user_login).first()

    # 2. Faqat Boss kira olishini tekshirish
    if not profile or not profile.is_boss:
        return redirect('/')

    # 3. FILTRLASH LOGIKASI:
    # - assignment_status='completed' -> Tugatilgan bo'lishi shart
    # - assigned_worker__is_boss=False -> Bosslar ro'yxatga kirmasin
    # - assigned_worker__guruh=profile.guruh -> Faqat o'z guruhidagi ishchilar
    tugatilgan_vazifalar = TrainChain.objects.filter(
        assignment_status='completed',
        assigned_worker__is_boss=False,
        assigned_worker__guruh=profile.guruh
    ).select_related('assigned_worker').order_by('-received_at')

    context = {
        'vazifalar': tugatilgan_vazifalar,
        'profile': profile,
        # Video manzili settings.py dagi static sozlamalariga mos bo'lishi kerak
        'video_url': '/static/uzb.mp4'
    }
    return render(request, 'boss_holat_list.html', context)
def vagon_hisoboti(request, train_id):
    """
    BOSS uchun: Tanlangan poezd ichidagi vagonlar holatini ko'rsatish.
    """
    user_login = request.session.get('user_login')
    profile = UserProfile.objects.filter(login=user_login).first()

    if not profile or not profile.is_boss:
        return redirect('/')

    # Tanlangan poezdni olish
    train = get_object_or_404(TrainChain, id=train_id)

    # Shu poezdga tegishli barcha vagonlarni olish
    vagonlar = Vagon.objects.filter(train=train).order_by('sequence_number')

    context = {
        'train': train,
        'vagonlar': vagonlar,
        'ishchi': train.assigned_worker  # Vazifani bajargan ishchi
    }
    return render(request, 'boss_vagon_detail.html', context)
def check_vagon_view(request, vagon_id):
    """ Vagonni SOZ deb belgilash """
    vagon = get_object_or_404(Vagon, id=vagon_id)
    vagon.is_checked = True
    vagon.has_issue = False
    vagon.comment = ""  # Izohni tozalaydi
    vagon.save()
    return redirect(request.META.get('HTTP_REFERER', '/'))
def vagon_muammo_yozish(request, vagon_id):
    """ Vagonda MUAMMO borligini yozish """
    if request.method == 'POST':
        vagon = get_object_or_404(Vagon, id=vagon_id)
        muammo_matni = request.POST.get('muammo_matni', '')

        vagon.is_checked = True
        vagon.has_issue = True
        vagon.comment = muammo_matni  # Sizda modelda 'comment' deb yozilgan
        vagon.save()

        # vagon.vagon_number ishlatildi
        messages.success(request, f"№{vagon.vagon_number} vagonidagi muammo qayd etildi.")

    return redirect(request.META.get('HTTP_REFERER', '/'))
def get_guruhlar(request):
    otryad_id = request.GET.get('otryad_id')
    guruhlar = IshchiGuruh.objects.filter(otryad_id=otryad_id).values('id', 'nomi')
    return JsonResponse(list(guruhlar), safe=False)
def train_list_view(request):
    user_login = request.session.get('user_login')
    if not user_login:
        return redirect('/login/')

    boss = UserProfile.objects.filter(login=user_login).first()
    if not boss or not boss.is_boss:
        return redirect('/second/')

    # FILTR:
    # 1. Otryad "Toshkent" bo'lishi kerak
    # 2. YOKI ishchisi yo'q bo'lsin (yangi poyezdlar)
    # 3. YOKI biriktirilgan ishchining guruhi "НОРВ-13" bo'lsin
    trains = TrainChain.objects.filter(
        otryad__nomi="Toshkent"
    ).filter(
        Q(assigned_worker__isnull=True) |
        Q(assigned_worker__guruh__nomi="НОРВ-13")
    ).select_related('assigned_worker', 'otryad').prefetch_related('wagons').order_by('-received_at')

    context = {
        'trains': trains,
        'boss': boss,
        'video_url': '/static/uzb.mp4', # static helper o'rniga to'g'ridan-to'g'ri yo'l
    }
    return render(request, 'train_list.html', context)
def transfer_train_data(request, train_id):
    if request.method == "POST":
        train = get_object_or_404(TrainChain, id=train_id)
        guruh_id = request.POST.get('guruh')

        # Yangi guruhni va o'sha guruhdagi mas'ul xodimni topamiz
        yangi_guruh = get_object_or_404(IshchiGuruh, id=guruh_id)
        # Guruhdagi boshliqni (is_boss=True) qidiramiz
        new_worker = UserProfile.objects.filter(guruh=yangi_guruh, is_boss=True).first()

        if not new_worker:
            # Agar boshliq bo'lmasa, guruhdagi birinchi uchragan xodimga beramiz
            new_worker = UserProfile.objects.filter(guruh=yangi_guruh).first()

        if new_worker:
            train.assigned_worker = new_worker
            train.save()

        return redirect('train_list.html')

def train_list_view(request):
    user_login = request.session.get('user_login')
    if not user_login:
        return redirect('/login/')

    boss = UserProfile.objects.filter(login=user_login).first()
    if not boss or not boss.is_boss:
        return redirect('/second/')

    # DINAMIK FILTR:
    # 1. Poyezd aynan shu kirgan bossning otryadida bo'lishi kerak
    # 2. VA (Yoki hali ishchisi yo'q, YOKI ishchisi aynan shu bossning guruhidan)
    trains = TrainChain.objects.filter(
        otryad=boss.otryad  # "Toshkent" emas, boss qaysi otryadda bo'lsa o'sha!
    ).filter(
        Q(assigned_worker__isnull=True) |
        Q(assigned_worker__guruh=boss.guruh) # "НОРВ-13" emas, bossning o'z guruhi!
    ).select_related('assigned_worker', 'otryad').prefetch_related('wagons').order_by('-received_at')

    context = {
        'trains': trains,
        'boss': boss,
        'video_url': '/static/uzb.mp4',
    }
    return render(request, 'train_list.html', context)
def malumot_uzatish_view(request):
    user_login = request.session.get('user_login')
    if not user_login:
        return redirect('/login/')

    boss = UserProfile.objects.get(login=user_login)

    # Faqat shu bossning guruhidagi ishchilarga biriktirilgan poyezdlar
    trains = TrainChain.objects.filter(
        assigned_worker__guruh=boss.guruh,
        assigned_worker__is_boss=False
    ).select_related('assigned_worker')

    otryadlar = Otryad.objects.all()

    context = {
        'trains': trains,
        'otryadlar': otryadlar,
        'display_name': boss.full_name or boss.login,
        'user_guruh_id': boss.guruh.id if boss.guruh else None,
    }
    return render(request, 'malumot_uzatish.html', context)




# 3. AJAX: Otryad tanlanganda guruhlarni qaytarish
def get_guruhlar_ajax(request):
    otryad_id = request.GET.get('otryad_id')
    guruhlar = Guruh.objects.filter(otryad_id=otryad_id).values('id', 'nomi')
    return JsonResponse(list(guruhlar), safe=False)


def transfer_train_api(request, train_id):
    if request.method == 'POST':
        otryad_id = request.POST.get('otryad')
        guruh_id = request.POST.get('guruh')

        if otryad_id and guruh_id:
            train = get_object_or_404(TrainChain, id=train_id)

            # Poyezdni yangi manzilga yo'naltirish
            train.otryad_id = otryad_id
            # Agar TrainChain-da guruh fieldini qo'shgan bo'lsangiz:
            # train.guruh_id = guruh_id

            # Eski ishchidan uzib qo'yish
            train.assigned_worker = None
            train.assignment_status = 'free'

            train.save()
            print(f"DEBUG: Poyezd {train.train_number} uzatildi: Otryad {otryad_id}, Guruh {guruh_id}")

            # XATOLIK SHU YERDA EDI:
            # Agar 'malumot_uzatish' degan name bo'lmasa, shunchaki URL yozing:
            return redirect('/malumot/')  # yoki o'sha sahifa URL manzili

    return redirect('/bosspage/')  # Xatolik bo'lsa bosh sahifaga


@csrf_exempt
def handle_acu_data(request):
    """
    Pythonanywhere serverida ACUdan JSON ma'lumotlarini qabul qilish.
    """
    if request.method == 'POST':
        try:
            # 1. JSON ma'lumotni o'qish
            data = json.loads(request.body)

            # ACU paketidan ma'lumotlarni olish
            train_num = data.get('train_number')
            v_count = data.get('vagon_count', 0)
            operation = data.get('operation', 'Прибытие')
            track_num = data.get('track_number', '--')
            asu_id_real = data.get('asu_id')
            weight = data.get('total_weight', 0)

            # 2. TOSHKENT VA НОРВ-13 NI ANIQLASH
            otryad = Otryad.objects.filter(nomi="Toshkent").first()
            guruh = IshchiGuruh.objects.filter(nomi="НОРВ-13", otryad=otryad).first()

            # НОРВ-13 ishchisini aniqlash (ID=5 yoki birinchisi)
            worker = UserProfile.objects.filter(guruh=guruh, id=5).first() or \
                     UserProfile.objects.filter(guruh=guruh).first()

            if not otryad or not worker:
                return JsonResponse({'status': 'error', 'message': 'Tizimda Toshkent/NORV-13 topilmadi'}, status=400)

            # 3. POYEZDNI YARATISH
            train = TrainChain.objects.create(
                asu_id=asu_id_real,
                train_number=train_num,
                operation=operation,
                vagon_count=v_count,
                total_weight=weight,
                received_at=timezone.now(),
                otryad=otryad,
                assigned_worker=worker,
                assignment_status='confirmed',
                track_number=track_num,
                is_processed=False
            )

            # 4. MONITORING UCHUN VAZIFA YARATISH
            task = TaskAssignment.objects.create(
                worker=worker,
                train_index=f"{train_num}-ACU",
                otryad=otryad,
                guruh=guruh,
                status='in_progress'
            )

            # 5. VAGONLARNI QABUL QILISH
            wagons_list = data.get('wagons', [])
            for i, v_data in enumerate(wagons_list, 1):
                Vagon.objects.create(
                    train=train,
                    task=task,
                    vagon_number=v_data.get('number'),
                    vagon_type=v_data.get('type', 'Грузовой'),
                    cargo_name=v_data.get('cargo', 'Нет данных'),
                    tartib_raqam=i,
                    sequence_number=i
                )

            return JsonResponse({
                'status': 'success',
                'message': f'Poyezd №{train_num} Pythonanywhere bazasiga yozildi',
                'train_id': train.id
            })

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    return JsonResponse({'status': 'error', 'message': 'Faqat POST so\'rov qabul qilinadi'}, status=405)