# ========================================
# urls.py — Core App (SkillHub Project)
# ========================================

from django.urls import path
from . import views

app_name = 'core'  # Namespace for URL resolution — allows "core:home" etc.

urlpatterns = [
    # ---------------- HOME & COURSE LIST ----------------
    path('', views.home, name='home'),  # Homepage — usually shows featured courses
    path('courses/', views.course_list, name='course_list'),  # All available courses
    path('course/<slug:slug>/', views.course_detail, name='course_detail'),  # Single course details page

    # ---------------- INSTRUCTOR COURSE CREATION ----------------
    path('instructor/create/', views.create_course, name='create_course'),  # Create a new course
    path('instructor/course/<int:pk>/edit/', views.edit_course, name='edit_course'),  # Edit existing course
    path('instructor/course/<int:pk>/delete/', views.delete_course, name='delete_course'),  # Delete a course

    # ---------------- ENROLLMENT & COURSE ACCESS ----------------
    path('enroll/<int:course_id>/', views.enroll_course, name='enroll_course'),  # Enroll in a free course
    path('course/<int:course_id>/content/', views.course_content, name='course_content'),  # View all lessons/modules of an enrolled course

    # ---------------- AUTHENTICATION ----------------
    path('accounts/register/', views.register_view, name='register'),  # User registration form
    path('accounts/login/', views.login_view, name='login'),  # Login page
    path('accounts/logout/', views.logout_view, name='logout'),  # Logout and redirect

    # ---------------- INSTRUCTOR DASHBOARD ----------------
    path("instructor/dashboard/", views.instructor_dashboard, name="instructor_dashboard"),

    path('instructor/course/<int:course_id>/module/add/', views.add_module, name='add_module'),  # Add new module to a course
    path('instructor/course/<int:course_id>/add-lesson/', views.add_lesson, name='add_lesson'),  # Add lessons under a module

    # ---------------- LESSON VIEWING ----------------
    path('course/<slug:course_slug>/lesson/<int:lesson_id>/', views.lesson_detail, name='lesson_detail'), 
    path('lesson/<int:lesson_id>/edit/', views.edit_lesson, name='edit_lesson'),

 # View individual lesson content/video

    # ---------------- COURSE PURCHASE & PAYMENT ----------------
    path('course/<int:course_id>/buy/', views.buy_course, name='buy_course'),  # Buy paid course (starts transaction)
    path('confirm-payment/<int:course_id>/', views.confirm_payment, name='confirm_payment'),
    path('course/<int:course_id>/payment-success/', views.payment_success, name='payment_success'),
    path('approve-payment/<int:payment_id>/', views.approve_payment, name='approve_payment'),

 # Payment success page
    path('manage-payments/', views.manage_payments, name='manage_payments'),  # Instructor view to verify and approve payments

    # ---------------- FEEDBACK & REVIEWS ----------------
    path('instructor/feedbacks/', views.manage_feedbacks, name='manage_feedbacks'),  # Admin/instructor manage feedback messages
    # urls.py
    path('course/<int:course_id>/review/', views.review_page, name='review_page'),
    # ---------------- REVIEW APPROVAL ----------------
    path('review/<int:review_id>/approve/', views.approve_review, name='approve_review'),
    path('review/<int:review_id>/delete/', views.delete_review, name='delete_review'),


 # Student adds a review for a course

    # ---------------- COURSE COMPLETION ----------------
    path('course/<int:course_id>/complete/', views.complete_course, name='complete_course'),  # Mark course as completed (for certificate generation)

    # ---------------- QUIZ MANAGEMENT ----------------
    path('instructor/course/<int:course_id>/add-quiz/', views.add_quiz, name='add_quiz'),



    path('instructor/manage-quizzes/<int:course_id>/', views.manage_quizzes, name='manage_quizzes'),
  # Instructor sees all quizzes
    path('instructor/quiz/<int:quiz_id>/edit/', views.edit_quiz, name='edit_quiz'),  # Edit quiz
    path('instructor/quiz/<int:quiz_id>/delete/', views.delete_quiz, name='delete_quiz'),  # Delete quiz
    path('instructor/quiz/<int:quiz_id>/add-question/', views.add_question, name='add_question'),  # Add questions to quiz
    path('instructor/quiz/<int:quiz_id>/questions/', views.view_quiz_questions, name='view_quiz_questions'),  # View all questions in a quiz
    path('instructor/question/<int:question_id>/edit/', views.edit_question, name='edit_question'),  # Edit a question
    path('instructor/question/<int:question_id>/delete/', views.delete_question, name='delete_question'),  # Delete a question
    path('quiz/<int:quiz_id>/', views.quiz_detail, name='quiz_detail'),

    # ---------------- QUIZ ATTEMPTS ----------------
    path('quiz/<int:quiz_id>/start/', views.start_quiz, name='start_quiz'),  # Student starts a quiz
    path('quiz/attempt/<int:attempt_id>/result/', views.quiz_result, name='quiz_result'),  # View quiz score/result
        path('quiz/submission/<int:attempt_id>/', views.view_quiz_submission, name='view_quiz_submission'),
        path('quiz/<int:quiz_id>/attempts/', views.view_quiz_attempts, name='view_quiz_attempts'),


    # ---------------- ASSIGNMENT MANAGEMENT ----------------
    path('instructor/course/<int:course_id>/add-assignment/', views.add_assignment, name='add_assignment'),  # Add assignment to course
    path('instructor/course/<int:course_id>/manage-assignments/', views.manage_assignments, name='manage_assignments'),  # View and manage all assignments in a course
    path('instructor/assignment/<int:assignment_id>/edit/', views.edit_assignment, name='edit_assignment'),  # Edit assignment
    path('instructor/assignment/<int:assignment_id>/delete/', views.delete_assignment, name='delete_assignment'),  # Delete assignment

    # ---------------- ASSIGNMENT SUBMISSIONS ----------------
    path('assignment/<int:assignment_id>/submit/', views.submit_assignment, name='submit_assignment'),  # Student uploads submission
    path('submission/<int:submission_id>/grade/', views.grade_submission, name='grade_submission'),

    # ---------------- CERTIFICATES ----------------
     # urls.py
     path('certificate/approve/<int:enrollment_id>/', views.approve_certificate, name='approve_certificate'),
     path('certificate/download/<slug:slug>/', views.download_certificate, name='download_certificate'),



    # ---------------- ENROLLMENT APPROVAL (ADMIN/INSTRUCTOR) ----------------
    path('instructor/enrollment/<int:enrollment_id>/approve/', views.approve_enrollment, name='approve_enrollment'),  # Instructor/admin approves a student's enrollment

    path("profile/", views.profile, name="profile"),
    path("profile/edit/", views.edit_profile, name="edit_profile"),

    # ---------------- STATIC INFO PAGES ----------------
    path('about/', views.about, name='about'),

    path('faqs/', views.faqs_page, name='faqs'),
    path('support/', views.support_page, name='support'),

    path('support/', views.support_view, name='support'),


    path('profile/update-instructor/', views.update_instructor_profile, name='update_instructor_profile'),


    path('certificate/approve/<int:enrollment_id>/', views.approve_certificate, name='approve_certificate'),
    path('certificate/download/<slug:slug>/', views.download_certificate, name='download_certificate'),


]
