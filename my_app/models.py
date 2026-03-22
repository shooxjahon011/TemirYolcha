
from django.db import models
from django.utils import timezone
from decimal import Decimal
from django.conf import settings


# 1. Otryadlar (Masalan: 1-Otryad, 2-Otryad)
class Otryad(models.Model):
    nomi = models.CharField(max_length=255)

    def __str__(self):
        return self.nomi


# 2. Ishchi Guruhlar (Otryadga tegishli guruhlar)
class IshchiGuruh(models.Model):
    nomi = models.CharField(max_length=100)
    otryad = models.ForeignKey(Otryad, on_delete=models.SET_NULL, related_name='guruhlar', null=True, blank=True)

    def __str__(self):
        return f"{self.nomi} ({self.otryad.nomi if self.otryad else 'Otryadsiz'})"



# 3. Foydalanuvchi Profili (Ishchi va Boshliqlar uchun)
class UserProfile(models.Model):
    full_name = models.CharField(max_length=255)
    login = models.CharField(max_length=100, unique=True)

    password = models.CharField(max_length=128)  # Hashlangan bo'lishi kerak
    phone = models.CharField(max_length=20)
    tabel_raqami = models.CharField(max_length=50, unique=True, blank=True, null=True)

    # Izolyatsiya va Guruhlash
    is_boss = models.BooleanField(default=False)  # Boshliqlarni ajratish uchun
    otryad = models.ForeignKey(Otryad, on_delete=models.SET_NULL, null=True, blank=True)
    guruh = models.ForeignKey(IshchiGuruh, on_delete=models.SET_NULL, null=True, blank=True)

    # Manzil ma'lumotlari
    viloyat = models.CharField(max_length=100, blank=True, null=True)
    shahar_tuman = models.CharField(max_length=100, blank=True, null=True)
    mahalla = models.CharField(max_length=100, blank=True, null=True)
    kocha = models.CharField(max_length=100, blank=True, null=True)
    uy_raqami = models.CharField(max_length=20, blank=True, null=True)

    # Ish ma'lumotlari
    razryad = models.CharField(max_length=10, blank=True, null=True)
    oklad = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))


    # Xavfsizlik va holat
    activation_code = models.CharField(max_length=10, blank=True, null=True)
    is_active = models.BooleanField(default=False)
    activated_at = models.DateTimeField(null=True, blank=True)
    last_seen = models.DateTimeField(auto_now=True)
    image = models.ImageField(upload_to='profiles/', null=True, blank=True)
    is_working = models.BooleanField(default=False)
    work_start_time = models.DateTimeField(null=True, blank=True)
    current_lat = models.FloatField(null=True, blank=True)
    current_lon = models.FloatField(null=True, blank=True)
    last_location_update = models.DateTimeField(null=True, blank=True)


    def __str__(self):
        role = "Boshliq" if self.is_boss else "Ishchi"
        return f"{self.full_name} ({role} - {self.tabel_raqami})"

class TaskAssignment(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Kutilmoqda'),
        ('in_progress', 'Jarayonda'),
        ('completed', 'Tugallangan'),
    ]

    # worker_full_name o'rniga UserProfile bilan bog'laymiz
    worker = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='tasks', null=True, blank=True)
    train_index = models.CharField(max_length=50)

    # Otryad va Guruh (Bularni ham UserProfile'dan avtomatik olish mumkin,
    # lekin vazifa doirasida o'zgarishi mumkin bo'lsa qoldiramiz)
    otryad = models.ForeignKey(Otryad, on_delete=models.SET_NULL, null=True, blank=True)
    guruh = models.ForeignKey(IshchiGuruh, on_delete=models.SET_NULL, null=True, blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    vaqt = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.worker.full_name} - {self.train_index}"
# 4. 24 Soatlik Lokatsiya Tarixi (Marshrutni chizish uchun)

# 6. Chat tizimi (Guruh bo'yicha ajratilgan)
class ChatMessage(models.Model):
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    guruh = models.ForeignKey(IshchiGuruh, on_delete=models.CASCADE)
    text = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to='chat_images/', null=True, blank=True)
    video = models.FileField(upload_to='chat_videos/', null=True, blank=True)
    voice = models.FileField(upload_to='chat_voices/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.login} xabari ({self.created_at.strftime('%Y-%m-%d %H:%M')})"

class WorkSchedule(models.Model):
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    date = models.DateField()
    oklad = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    norma_soati = models.FloatField(default=0)
    ishlagan_soati = models.FloatField(default=0)
    tungi_soati = models.FloatField(default=0)
    bayram_soati = models.FloatField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.login} - {self.date}"
class UserLocation(models.Model):
    user = models.OneToOneField(UserProfile, on_delete=models.CASCADE, related_name='current_location')
    latitude = models.FloatField()
    longitude = models.FloatField()
    updated_at = models.DateTimeField(auto_now=True)
    is_working = models.BooleanField(default=False)
    work_start_time = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=False)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.full_name} - {self.latitude}, {self.longitude}"

class LocationHistory(models.Model):
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    latitude = models.FloatField()
    longitude = models.FloatField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']


class TrainChain(models.Model):
    # Asosiy ID (ASU dagi ID bilan bir xil bo'ladi)
    asu_id = models.IntegerField(unique=True)
    train_number = models.CharField(max_length=50)
    # YANGI QATOR:
    otryad = models.ForeignKey('Otryad', on_delete=models.SET_NULL, null=True, blank=True)
    assigned_worker = models.ForeignKey('UserProfile', on_delete=models.SET_NULL, null=True, blank=True)
    # 1. Путь
    track_number = models.CharField(max_length=10, null=True, blank=True)
    # 2. Операция
    operation = models.CharField(max_length=50, null=True, blank=True)
    # 3. Поезд (Raqami)

    guruh = models.ForeignKey('IshchiGuruh', on_delete=models.SET_NULL, null=True, blank=True)
    # 4. Форм (Формирование)
    form_code = models.CharField(max_length=20, null=True, blank=True)
    # 5. Сост (Состав)
    sostav_code = models.CharField(max_length=20, null=True, blank=True)
    # 6. Назн (Назначение)
    nazn_code = models.CharField(max_length=20, null=True, blank=True)
    # 7. СостНЛП
    nlp_code = models.CharField(max_length=20, null=True, blank=True)
    # 8-9. Дата va Время (received_at ichida ikkalasi ham bo'ladi)
    received_at = models.DateTimeField()
    # 10. Тип
    type_code = models.CharField(max_length=20, null=True, blank=True)
    # 11. Ваг (Vagonlar soni)
    vagon_count = models.IntegerField(default=0)
    # 12. УДЛ (Условная длина)
    udl_code = models.CharField(max_length=20, null=True, blank=True)
    # 13. Вес (Vazni)
    total_weight = models.IntegerField(default=0)
    # 14. Охр (Ohrana)
    oxr_code = models.CharField(max_length=10, null=True, blank=True)
    # 15. Лок (Lokomotiv)
    lok_code = models.CharField(max_length=10, null=True, blank=True)
    assigned_worker = models.ForeignKey(
        UserProfile,  # <--- Shuni UserProfile qiling
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='assigned_trains'
    )
    # models.py ichida
    assignment_status = models.CharField(
        max_length=20,
        choices=[
            ('free', "Bo'sh"),
            ('pending', 'Kutilmoqda'),
            ('confirmed', 'Biriktirilgan'),
            ('completed', 'Tugatildi'),  # <--- Shuni qo'shing
        ],
        default='free'
    )

    # Qo'shimcha maydonlar
    is_processed = models.BooleanField(default=False)  # O'tgan-o'tmagani
    uzb_comments = models.TextField(null=True, blank=True)  # Bizning qaydlar

    def __str__(self):
        return f"{self.train_number} - {self.operation}"


class Vagon(models.Model):
    # Bu qator vagonni qaysi poezdga tegishli ekanini bog'laydi
    train = models.ForeignKey(TrainChain, on_delete=models.CASCADE, related_name='wagons')

    # Rasmda va ASUda bo'ladigan vagon ma'lumotlari
    vagon_number = models.CharField(max_length=20, verbose_name="Vagon raqami")
    vagon_type = models.CharField(max_length=50, null=True, blank=True, verbose_name="Turi")
    cargo_weight = models.IntegerField(default=0, verbose_name="Yuk vazni (kg)")
    cargo_name = models.CharField(max_length=255, null=True, blank=True, verbose_name="Yuk nomi")
    is_checked = models.BooleanField(default=False)  # Tekshirildimi?
    has_issue = models.BooleanField(default=False)  # Muammo bormi?
    comment = models.TextField(null=True, blank=True)
    task = models.ForeignKey(TaskAssignment, on_delete=models.CASCADE, related_name='vagonlar')
    tartib_raqam = models.IntegerField()  # 1, 2, 3...
    vagon_identifikator = models.CharField(max_length=20, unique=True)  # 353623355

    # Qo'shimcha (vagon tartib raqami poezd ichida)
    sequence_number = models.IntegerField(default=1)


    def __str__(self):
        return f"Vagon {self.vagon_number} (Poezd: {self.train.train_number})"