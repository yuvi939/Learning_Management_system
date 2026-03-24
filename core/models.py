# ==========================
# MODELS.PY — SkillHub LMS
# ==========================

from django.db import models
from django.contrib.auth.models import User
from django.core.validators import FileExtensionValidator
from django.utils import timezone
from django.utils.text import slugify


# -------------------------
# Profile: extends default Django User
# ------------------------

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    is_instructor = models.BooleanField(default=False)
    specialization = models.CharField(max_length=100, blank=True)
    experience = models.IntegerField(blank=True, null=True)
    bio = models.TextField(blank=True)
    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} Profile"

# -------------------------
# Category: groups courses by topic (e.g., Python, AI)
# -------------------------
class Category(models.Model):
    name = models.CharField(max_length=100)
    image = models.ImageField(upload_to='categories/', blank=True, null=True)

    def __str__(self):
        return self.name


# -------------------------
# Course: main course model created by instructors
# -------------------------
class Course(models.Model):
    instructor = models.ForeignKey(User,related_name='courses', on_delete=models.CASCADE)  # Creator of the course
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)  # SEO-friendly URL name (auto-generated)
    short_description = models.TextField()
    description = models.TextField()
    price = models.DecimalField(max_digits=8, decimal_places=2)  # e.g. 999.99
    cover = models.ImageField(upload_to='covers/', blank=True, null=True)  # Course image
    published = models.BooleanField(default=False)  # Only visible when published=True
    category = models.ForeignKey('Category', on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)  # Auto timestamp on create
    updated_at = models.DateTimeField(auto_now=True)  # Auto timestamp on update

    def save(self, *args, **kwargs):
        # Auto-generate a unique slug when saving
        if not self.slug:
            base_slug = slugify(self.title)
            unique_slug = base_slug
            counter = 1
            while Course.objects.filter(slug=unique_slug).exists():
                unique_slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = unique_slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


# -------------------------
# Module: logical sections inside a course
# e.g., Module 1: Basics, Module 2: Advanced
# -------------------------
class Module(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='modules')
    title = models.CharField(max_length=255)
    order = models.PositiveIntegerField(default=0)  # Determines display order

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.order}. {self.title}"


# -------------------------
# Lesson: individual learning content (text + optional video)
# -------------------------
class Lesson(models.Model):
    module = models.ForeignKey('Module', related_name='lessons', on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    order = models.PositiveIntegerField(default=1)
    content = models.TextField(null=True, blank=True)  # Lesson text or HTML content
    video = models.FileField(upload_to='lesson_videos/', blank=True, null=True)  # Optional video upload

    def __str__(self):
        return self.title
    
class Assignment(models.Model):
    module = models.ForeignKey(Module, related_name='module_assignments', on_delete=models.CASCADE,null=True,blank=True)
    course = models.ForeignKey('Course', on_delete=models.CASCADE, related_name='assignments')
    title = models.CharField(max_length=200)
    description = models.TextField()
    due_date = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.title


# -------------------------
class Enrollment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='enrollments')
    course = models.ForeignKey('Course', on_delete=models.CASCADE, related_name='enrollments')
    approved = models.BooleanField(default=False)
    enrolled_at = models.DateTimeField(default=timezone.now)
    completed_lessons = models.ManyToManyField('Lesson', blank=True, related_name='completed_by')
    completed_assignments = models.ManyToManyField('Assignment', blank=True, related_name='assignment_completed_by')
    completed_quizzes = models.ManyToManyField('Quiz', blank=True, related_name='quiz_completed_by')
    completed = models.BooleanField(default=False)
    certificate_approved = models.BooleanField(default=False)
    certificate_issued = models.BooleanField(default=False)
    certificate_generated_on = models.DateTimeField(null=True, blank=True)  # ✅ new field

    class Meta:
        unique_together = ('user', 'course')

    def check_completion(self):
        total_lessons = Lesson.objects.filter(module__course=self.course).count()
        total_assignments = Assignment.objects.filter(course=self.course).count()
        total_quizzes = Quiz.objects.filter(module__course=self.course).count()

        completed_lessons = self.completed_lessons.count()
        completed_assignments = self.completed_assignments.count()
        completed_quizzes = self.completed_quizzes.count()

        if (
            total_lessons > 0 and completed_lessons == total_lessons and
            total_assignments > 0 and completed_assignments == total_assignments and
            total_quizzes > 0 and completed_quizzes == total_quizzes
        ):
            self.completed = True
            self.save()
        else:
            self.completed = False
            self.save()

    def __str__(self):
        return f"{self.user.username} -> {self.course.title}"



# -------------------------
# Review: students leave ratings and comments on courses
# -------------------------
class Review(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.PositiveSmallIntegerField(default=5)
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.user.username} - {self.course.title}"


# -------------------------
# Feedback: general site feedback form (homepage)
# -------------------------
class Feedback(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, null=True, blank=True)
    message = models.TextField()
    reply=models.TextField(null=True,default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    approved = models.BooleanField(default=False)

    def __str__(self):
        if self.user:
            return f"{self.user.username} - {self.message[:20]}"
        return f"Anonymous - {self.message[:20]}"



# -------------------------
# Quiz: part of course for self-assessment
# -------------------------

class Quiz(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='quizzes', null=True, blank=True)
    module = models.ForeignKey('Module', on_delete=models.CASCADE, related_name='quizzes', null=True, blank=True)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    total_marks = models.PositiveIntegerField(null=True, blank=True)   # optional
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title}"



class Question(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='questions')
    question_text = models.CharField(max_length=500)
    option1 = models.CharField(max_length=255)
    option2 = models.CharField(max_length=255)
    option3 = models.CharField(max_length=255)
    option4 = models.CharField(max_length=255)
    correct_option = models.CharField(max_length=1, choices=[
    ('A', 'Option A'),
    ('B', 'Option B'),
    ('C', 'Option C'),
    ('D', 'Option D')
])


    def __str__(self):
        return f"{self.quiz.title} - {self.question_text[:40]}"


class CompletedQuiz(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE)
    score = models.FloatField(default=0)
    completed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.student.username} - {self.quiz.title} ({self.score}%)"

# -------------------------
# Assignment: instructor uploads a task for students to submit



class Submission(models.Model):
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name='submissions')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='submissions')  # was student
    submitted_file = models.FileField(upload_to='submissions/')
    submitted_at = models.DateTimeField(auto_now_add=True)
    grade = models.CharField(max_length=10, null=True, blank=True)
    feedback = models.TextField(null=True, blank=True)
    graded_at = models.DateTimeField(null=True, blank=True)
    graded_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='graded_submissions')

    def __str__(self):
        return f"{self.user.username} - {self.assignment.title}"

# -------------------------
# Certificate: issued when student completes a course
# -------------------------
class Certificate(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)  # was student
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    issued_date = models.DateTimeField(default=timezone.now)
    certificate_file = models.FileField(upload_to='certificates/', null=True, blank=True)

    def __str__(self):
        return f"Certificate - {self.user.username} ({self.course.title})"
 # PDF file

    


# -------------------------
# QuizAttempt: tracks each student's quiz results
# -------------------------
class QuizAttempt(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='attempts')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='quiz_attempts',null=True)  # was student
    score = models.FloatField(default=0)
    total_questions = models.PositiveIntegerField(default=0)
    correct_answers = models.PositiveIntegerField(default=0)
    completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)


    def total_marks(self):
        return self.total_questions 
    

    def mark_completed(self):
        """Mark quiz as completed for this student."""
        self.completed = True
        self.save()

    # Use .user instead of .student
        enrollment = Enrollment.objects.filter(user=self.user, course=self.quiz.course).first()
        if enrollment:
            enrollment.completed_quizzes.add(self.quiz)
        enrollment.save()


class SupportMessage(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Support from {self.name} ({self.email})"
    
class QuizAnswer(models.Model):
    attempt = models.ForeignKey(QuizAttempt, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_option = models.IntegerField()


class Payment(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    course = models.ForeignKey('Course', on_delete=models.CASCADE)
    transaction_id = models.CharField(max_length=100)
    mobile = models.CharField(max_length=15)
    
    # ✅ Keep a boolean for quick approval check
    approved = models.BooleanField(default=False)
    
    # ✅ Amount of payment
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    # ✅ Status for admin workflow
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.course.title} - {self.status}"

    # Optional: automatically sync approved boolean with status
    def save(self, *args, **kwargs):
        if self.status == 'approved':
            self.approved = True
        elif self.status in ['pending', 'rejected']:
            self.approved = False
        super().save(*args, **kwargs)
