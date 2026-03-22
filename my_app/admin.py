from django.contrib import admin
from .models import UserProfile, WorkSchedule  # IshHaqi bu yerdan olib tashlandi

# 1. UserProfile (Foydalanuvchilar profili)
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('login', 'image_display')
    search_fields = ('login',)

    def image_display(self, obj):
        if obj.image:
            return "Bor"
        return "Yo'q"

    image_display.short_description = "Rasm"


# 2. WorkSchedule (Kunlik jadval - Tungi soat va Norma soati bilan)
@admin.register(WorkSchedule)
class WorkScheduleAdmin(admin.ModelAdmin):
    # Siz xohlagandek tartib: Norma soati okladdan oldin
    list_display = (
        'user',
        'date',
        'norma_soati',
        'oklad',
        'ishlagan_soati',
        'tungi_soati',
        'bayram_soati'
    )

    list_filter = ('date', 'user')
    search_fields = ('user__login', 'date')

    # Ma'lumot qo'shish oynasidagi maydonlar tartibi
    fields = ('user', 'date', 'norma_soati', 'oklad', 'ishlagan_soati', 'tungi_soati', 'bayram_soati')

    date_hierarchy = 'date'