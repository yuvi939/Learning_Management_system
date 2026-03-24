# Register your models here.
from django.contrib import admin
from .models import Profile, Category, Course, Module, Lesson, Enrollment, Review, Quiz, Question, Assignment, Submission,Payment

admin.site.register(Profile)
admin.site.register(Category)

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('title', 'instructor', 'price', 'published',)
    prepopulated_fields = {'slug': ('title',)}

class ModuleInline(admin.StackedInline):
    model = Module
    extra = 0

class LessonInline(admin.StackedInline):
    model = Lesson
    extra = 0

@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'order')
    inlines = [LessonInline]

@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ('title', 'module', 'order')

@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ('user', 'course', 'enrolled_at', 'completed')

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('course', 'user', 'rating', 'created_at')

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('user', 'course', 'transaction_id', 'status', 'created_at')
    list_filter = ('status', 'created_at')





admin.site.register(Quiz)
admin.site.register(Question)
admin.site.register(Assignment)
admin.site.register(Submission)
