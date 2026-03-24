# ========================================
# forms.py — Core App (SkillHub Project)
# ========================================
# This file contains Django form classes used to collect and validate
# user input (like registration, course creation, lesson upload, etc.)
# before saving to the database.

from django import forms
from django.contrib.auth.models import User
from .models import Course, Lesson, Module, Review,SupportMessage


# ---------------- USER REGISTRATION FORM ----------------
from django import forms
from django.contrib.auth.models import User
from .models import Profile

class RegisterForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)
    confirm_password = forms.CharField(widget=forms.PasswordInput)
    avatar = forms.ImageField(required=False, label="Profile Picture")  # ✅ new field

    class Meta:
        model = User
        fields = ['username', 'email', 'password']  # ❌ remove avatar here — it’s not part of User model

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('password') != cleaned.get('confirm_password'):
            self.add_error('confirm_password', "Passwords must match.")
        return cleaned


# ---------------- COURSE CREATION FORM ----------------
class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = [
            'title', 'short_description', 'description',
            'price', 'cover', 'published', 'category'
        ]
        # Labels for form display (optional but improves clarity)
        labels = {
            'title': 'Course Title',
            'short_description': 'Short Summary',
            'description': 'Detailed Description',
            'price': 'Course Price (₹)',
            'cover': 'Course Image',
            'published': 'Publish Now?'
        }
        # Widgets define the form input UI styling (Bootstrap-friendly)
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Learn Python from Scratch'
            }),
            'short_description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Short course summary...'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Write full description here...'
            }),
            'price': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. 499'
            }),
            'cover': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'published': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


# ---------------- MODULE CREATION FORM ----------------
class ModuleForm(forms.ModelForm):
    # Used by instructor to add a module (chapter) inside a course
    class Meta:
        model = Module
        fields = ['title', 'order']


# ---------------- LESSON CREATION FORM ----------------
class LessonForm(forms.ModelForm):
    # Used by instructor to add a lesson (topic/video) in a module
    class Meta:
        model = Lesson
        fields = ['title', 'order', 'content', 'video']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter lesson title'
            }),
            'order': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Lesson order'
            }),
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Write lesson details here...'
            }),
            'video': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }


# ---------------- COURSE REVIEW FORM ----------------
class ReviewForm(forms.ModelForm):
    # Allows enrolled students to leave a rating and comment
    class Meta:
        model = Review
        fields = ['rating', 'comment']
        widgets = {
            'rating': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'max': 5
            }),
            'comment': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            }),
        }



class SupportForm(forms.Form):
    name = forms.CharField(label="Your Name", max_length=100)
    email = forms.EmailField(label="Your Email")
    subject = forms.CharField(label="Subject", max_length=200)
    message = forms.CharField(label="Message", widget=forms.Textarea(attrs={'rows': 4}))