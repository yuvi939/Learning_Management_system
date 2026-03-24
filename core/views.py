# Create your views here.
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from .models import *
from .form import RegisterForm, CourseForm,LessonForm,ModuleForm,ReviewForm,SupportForm
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.http import FileResponse
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.http import FileResponse
from django.template.loader import render_to_string
from reportlab.pdfgen import canvas
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.forms import UserChangeForm, PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from django.http import FileResponse
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib import colors
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Course, Certificate
import io
def home(request):
    # Show courses if user is logged in
    my_courses = []
    if request.user.is_authenticated:
        my_courses = Enrollment.objects.filter(
            user=request.user
        ).select_related('course')

    newest = Course.objects.filter(published=True).order_by('-created_at')[:6]
    categories = Category.objects.all()[:5]

    # Handle feedback submission
    if request.method == "POST":
        if not request.user.is_authenticated:
            messages.error(request, "Please login to submit feedback.")
            return redirect('core:login')

        # Save feedback
        Feedback.objects.create(
            user=request.user,
            message=request.POST.get("message")
        )

        # Send thank-you email
        send_mail(
            subject="Thanks for your feedback!",
            message=f"Dear {request.user.username},\n\nThank you for your feedback! ❤️",
            from_email="yuvrajsonawane939@gmail.com",
            recipient_list=[request.user.email],
            fail_silently=True,
        )

        messages.success(request, "Your feedback has been submitted successfully!")
        return redirect("core:home")

    # Show approved feedback
    feedbacks = Feedback.objects.filter(approved=True).order_by('-created_at')[:3]

    return render(request, 'core/home.html', {
        'my_courses': my_courses,
        'newest': newest,
        'categories': categories,
        'feedbacks': feedbacks,
    })




def course_list(request):
    q = request.GET.get('q') or ''
    selected_category = request.GET.get('category')

    courses = Course.objects.filter(published=True, title__icontains=q)
    if selected_category:
        courses = courses.filter(category__id=selected_category)

    categories = Category.objects.all()

    return render(request, 'core/course_list.html', {
        'courses': courses,
        'categories': categories,
        'selected_category': selected_category,
    })
    

@login_required(login_url='core:login')
def course_detail(request, slug):
    """
    Display course detail with modules, lessons, assignments, quizzes, reviews.
    Handles payment access, progress, and review submissions.
    """

    # 1️⃣ Get course and prefetch related modules/lessons/quizzes/assignments/reviews
    course = get_object_or_404(
        Course.objects.prefetch_related(
            'modules__lessons',
            'modules__module_assignments',
            'modules__quizzes',
            'reviews'
        ),
        slug=slug,
        published=True
    )

    # 2️⃣ Check payment
    payment = Payment.objects.filter(user=request.user, course=course).first()
    payment_approved = payment.approved if payment else False
    payment_pending = payment and not payment.approved

    # 3️⃣ If no payment → restrict access
    if not payment:
        return render(request, 'core/course_detail.html', {
            'course': course,
            'payment_approved': False,
            'payment_pending': False
        })

    # 4️⃣ If payment pending → show pending page
    if payment_pending:
        return render(request, 'core/confirm_payment.html', {'course': course})

    # 5️⃣ Check enrollment & progress
    enrolled = Enrollment.objects.filter(user=request.user, course=course).first()
    progress = 0
    course_completed = False

    # Get all lessons for the course (via modules)
    all_lessons = Lesson.objects.filter(module__course=course)
    all_assignments = Assignment.objects.filter(module__course=course)
    all_quizzes = Quiz.objects.filter(module__course=course)

    if enrolled:
        total_items = all_lessons.count() + all_assignments.count() + all_quizzes.count()
        completed_items = (
            enrolled.completed_lessons.count()
            + enrolled.completed_assignments.count()
            + enrolled.completed_quizzes.count()
        )
        progress = (completed_items / total_items * 100) if total_items > 0 else 0
        enrolled.completed = completed_items >= total_items and total_items > 0
        enrolled.save()
        course_completed = enrolled.completed

    # 6️⃣ Handle review form submission
    if request.method == 'POST':
        if not enrolled:
            messages.warning(request, "You must be enrolled to post a review.")
            return redirect('core:course_detail', slug=course.slug)

        form = ReviewForm(request.POST)
        if form.is_valid():
            if Review.objects.filter(course=course, user=request.user).exists():
                messages.warning(request, "You have already reviewed this course.")
                return redirect('core:course_detail', slug=course.slug)

            review = form.save(commit=False)
            review.course = course
            review.user = request.user
            review.save()

            send_mail(
                subject="Thanks for your feedback!",
                message=f"Hi {request.user.username},\n\nThanks for reviewing '{course.title}'.",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[request.user.email],
                fail_silently=True,
            )

            messages.success(request, "Your review has been added successfully!")
            return redirect('core:course_detail', slug=course.slug)
    else:
        form = ReviewForm()

    reviews = course.reviews.order_by('-created_at')

    # 7️⃣ Render template with context
    return render(request, 'core/course_content.html', {
        'course': course,
        'modules': course.modules.all(),
        'lessons': all_lessons,
        'assignments': all_assignments,
        'quizzes': all_quizzes,
        'enrolled': enrolled,
        'payment_approved': payment_approved,
        'payment_pending': payment_pending,
        'progress': round(progress, 2),
        'course_completed': course_completed,
        'form': form,
        'reviews': reviews,
    })
@login_required
def create_course(request):
    if not request.user.profile.is_instructor:
        messages.error(request, "You must be an instructor to create courses.")
        return redirect('core:home')

    if request.method == "POST":
        form = CourseForm(request.POST, request.FILES)
        if form.is_valid():
            course = form.save(commit=False)
            course.instructor = request.user
            course.save()
            messages.success(request, "Course created successfully!")
            return redirect('core:instructor_dashboard')
    else:
        form = CourseForm()

    return render(request, 'core/create_course.html', {'form': form})


@login_required
def enroll_course(request, course_id):
    course = get_object_or_404(Course, id=course_id, published=True)
    Enroll, created = Enrollment.objects.get_or_create(user=request.user, course=course)
    if created:
        messages.success(request, f"You are enrolled in {course.title}")
    else:
        messages.info(request, "Already enrolled.")
    return redirect('core:course_detail', slug=course.slug)

@login_required
def course_content(request, course_id):
    course = get_object_or_404(Course, id=course_id)

    payment = Payment.objects.filter(user=request.user, course=course).last()
    payment_approved = payment.status == "APPROVED" if payment else False

    if not payment_approved:
        messages.error(request, "You need to purchase this course first!")
        return redirect('core:course_detail', slug=course.slug)

    modules = Module.objects.filter(course=course)
    lessons = Lesson.objects.filter(course=course)
    quizzes = Quiz.objects.filter(course=course)
    assignments = Assignment.objects.filter(course=course)

    return render(request, 'core/course_content.html', {
        'course': course,
        'modules': modules,
        'lessons': lessons,
        'quizzes': quizzes,
        'assignments': assignments,
        'payment_approved': payment_approved
    })



def register_view(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST, request.FILES)
        if form.is_valid():
            user = User.objects.create_user(
                username=form.cleaned_data['username'],
                email=form.cleaned_data['email'],
                password=form.cleaned_data['password']
            )

            # Handle avatar safely
            avatar = form.cleaned_data.get('avatar')
            profile, created = Profile.objects.get_or_create(user=user)
            if avatar:
                profile.avatar = avatar
            profile.save()

            messages.success(request, "✅ Account created successfully! You can now log in.")
            return redirect('core:login')
    else:
        form = RegisterForm()

    return render(request, 'core/auth/register.html', {'form': form})



def login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('core:profile')
        else:
            error = "Invalid credentials"
            return render(request, 'core/auth/login.html', {'error': error})
    return render(request, 'core/auth/login.html')


def logout_view(request):
    logout(request)
    return redirect('core:home')


@login_required
def instructor_dashboard(request):
    user = request.user

    # All courses of this instructor
    courses = Course.objects.filter(instructor=user)

    # ----------------------
    # Assignments (course-level + module-level)
    # ----------------------
    assignments = Assignment.objects.filter(
        models.Q(course__in=courses) |
        models.Q(module__course__in=courses)
    ).select_related('course', 'module')

    # ----------------------
    # Submissions for these assignments
    # ----------------------
    submissions = Submission.objects.filter(
        assignment__in=assignments
    ).select_related('user', 'assignment')

    # ----------------------
    # Quizzes (course-level + module-level)
    # ----------------------
    quizzes = Quiz.objects.filter(
        models.Q(course__in=courses) |
        models.Q(module__course__in=courses)
    )

    # Quiz attempts
    quiz_submissions = QuizAttempt.objects.filter(
        quiz__in=quizzes
    ).select_related('user', 'quiz')

    # ----------------------
    # Enrollments for certificate management
    # ----------------------
    enrollments = Enrollment.objects.filter(course__in=courses).select_related('user','course')
    pending_enrollments = enrollments.filter(approved=False)

    # ----------------------
    # Feedback & Reviews & Payments
    # ----------------------
    feedbacks = Feedback.objects.filter(course__in=courses).select_related('user','course')
    reviews = Review.objects.filter(course__in=courses).select_related('user','course')
    payments = Payment.objects.filter(course__in=courses).select_related('user','course')

    context = {
        'courses': courses,
        'assignments': assignments,
        'submissions': submissions,
        'quiz_submissions': quiz_submissions,
        'enrollments': enrollments,
        'pending_enrollments': pending_enrollments,
        'feedbacks': feedbacks,
        'reviews': reviews,
        'payments': payments,
    }

    return render(request, 'core/instructor_dashboard.html', context)



@login_required
def edit_course(request, pk):
    course = get_object_or_404(Course, pk=pk, instructor=request.user)
    if request.method == 'POST':
        form = CourseForm(request.POST, request.FILES, instance=course)
        if form.is_valid():
            form.save()
            messages.success(request, "Course updated successfully.")
            return redirect('core:instructor_dashboard')
    else:
        form = CourseForm(instance=course)
    return render(request, 'core/instructor_edit_course.html', {'form': form, 'course': course})


@login_required
def delete_course(request, pk):
    course = get_object_or_404(Course, pk=pk, instructor=request.user)
    course.delete()
    messages.success(request, "Course deleted successfully.")
    return redirect('core:instructor_dashboard')


@login_required
def add_module(request, course_id):
    course = get_object_or_404(Course, id=course_id, instructor=request.user)
    if request.method == 'POST':
        form = ModuleForm(request.POST)
        if form.is_valid():
            module = form.save(commit=False)
            module.course = course
            module.save()
            messages.success(request, "Module added successfully.")
            return redirect('core:instructor_dashboard')
    else:
        form = ModuleForm()
    return render(request, 'core/instructor_add_module.html', {'form': form, 'course': course})
@login_required
def add_lesson(request, course_id):
    course = get_object_or_404(Course, id=course_id)

    # जर या कोर्समध्ये एकच module असेल तर तो auto select कर
    modules = course.modules.all()
    if not modules.exists():
        messages.warning(request, "Please create a module before adding a lesson.")
        return redirect('core:add_module', course.id)

    if request.method == 'POST':
        form = LessonForm(request.POST, request.FILES)
        if form.is_valid():
            lesson = form.save(commit=False)
            # 👉 पहिला module auto assign करा (किंवा user select करू शकतो)
            lesson.module = modules.first()
            lesson.save()
            messages.success(request, "Lesson added successfully!")
            return redirect('core:instructor_dashboard')
    else:
        form = LessonForm()

    return render(request, 'core/add_lesson.html', {'form': form, 'course': course})

@login_required
def lesson_detail(request, course_slug, lesson_id):
    course = get_object_or_404(Course, slug=course_slug)
    lesson = get_object_or_404(Lesson, id=lesson_id, module__course=course)

    # फक्त enrolled किंवा खरीदी केलेल्या user ला access
    enrolled = Enrollment.objects.filter(user=request.user, course=course).first()
    if not enrolled:
        return redirect('core:course_detail', slug=course.slug)

    return render(request, 'core/lesson_detail.html', {
        'course': course,
        'lesson': lesson,
        'enrolled': enrolled,
    })

from django.utils import timezone

@login_required
def buy_course(request, course_id):
    """User submits payment proof and awaits instructor/admin approval."""
    course = get_object_or_404(Course, id=course_id)

    if request.method == "POST":
        transaction_id = request.POST.get("transaction_id")
        mobile = request.POST.get("mobile")
        screenshot = request.FILES.get("screenshot")  # optional proof image

        # Save enrollment as 'pending approval'
        enrollment, created = Enrollment.objects.get_or_create(
            user=request.user,
            course=course,
            defaults={'approved': False}
        )

        if not created:
            messages.info(request, "You already submitted payment for this course.")
            return redirect("core:course_detail", slug=course.slug)

        # Save transaction details if your model has those fields
        enrollment.transaction_id = transaction_id
        enrollment.mobile = mobile
        if screenshot:
            enrollment.payment_proof = screenshot
        enrollment.save()

        # Confirmation message
        send_mail(
            subject=f"Payment Received for {course.title}",
            message=f"Hi {request.user.username},\n\nYour payment for '{course.title}' has been submitted successfully.\nWe will verify it shortly.",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[request.user.email],
            fail_silently=True,
        )

        messages.info(request, "🕓 Payment submitted for verification. You’ll be approved soon!")
        return redirect("core:course_detail", slug=course.slug)

    return render(request, "core/buy_course.html", {"course": course})

@login_required
def payment_success(request, course_id):
    """Confirmation page after successful approval."""
    course = get_object_or_404(Course, id=course_id)
    enrollment = Enrollment.objects.filter(user=request.user, course=course, approved=True).first()

    if not enrollment:
        messages.error(request, "Your payment is still pending approval.")
        return redirect("core:course_detail", slug=course.slug)

    return render(request, 'core/payment_success.html', {'course': course})


@staff_member_required
def approve_enrollment(request, enrollment_id):
    enrollment = Enrollment.objects.get(id=enrollment_id)
    enrollment.approved = True
    enrollment.save()
    return redirect('core:instructor_dashboard')


@login_required
def approve_payment(request, payment_id):
    payment = get_object_or_404(Payment, id=payment_id)

    # Only admin can approve
    if request.user.is_staff:
        if not payment.approved:
            payment.approved = True
            payment.save()

            # ✅ Auto-enroll the user if not already enrolled
            enrollment, created = Enrollment.objects.get_or_create(
                user=payment.user,
                course=payment.course
            )

            if created:
                messages.success(request, f"{payment.user.username} has been enrolled in {payment.course.title} and payment approved.")
            else:
                messages.info(request, f"{payment.user.username} is already enrolled in {payment.course.title}. Payment approved.")

        else:
            messages.info(request, "Payment already approved.")

    return redirect('core:instructor_dashboard')

@login_required
def manage_feedbacks(request):
    # Only instructors can manage feedbacks
    if not hasattr(request.user, 'profile') or not request.user.profile.is_instructor:
        messages.error(request, "Access restricted to instructors.")
        return redirect('core:home')

    # Fetch all feedbacks with related user and course
    feedbacks = Feedback.objects.select_related('user', 'course').all().order_by('-created_at')

    if request.method == 'POST':
        feedback_id = request.POST.get('feedback_id')
        action = request.POST.get('action')
        feedback = get_object_or_404(Feedback, id=feedback_id)

        if action == 'approve':
            feedback.approved = True
            feedback.save()
            messages.success(request, "Feedback approved!")
        elif action == 'delete':
            feedback.delete()
            messages.success(request, "Feedback deleted!")

        return redirect('core:manage_feedbacks')

    return render(request, 'core/instructor_manage_feedbacks.html', {'feedbacks': feedbacks})


@login_required
def add_review(request, slug):
    course = get_object_or_404(Course, slug=slug)
    enrolled = course.enrollments.filter(user=request.user).exists()

    if not enrolled:
        messages.error(request, "You must enroll in the course before leaving a review.")
        return redirect('core:course_detail', slug=slug)

    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.course = course
            review.user = request.user
            review.save()
            messages.success(request, "✅ Thank you for your review!")
            return redirect('core:course_detail', slug=slug)
    return redirect('core:course_detail', slug=slug)

@login_required
def manage_reviews(request):
    if not request.user.is_staff and not request.user.is_superuser:
        return redirect('core:home')

    from .models import Review
    reviews = Review.objects.all().order_by('-created_at')

    if request.method == "POST":
        rid = request.POST.get("review_id")
        action = request.POST.get("action")
        review = Review.objects.get(id=rid)
        if action == "delete":
            review.delete()
        elif action == "approve":
            review.approved = True
            review.save()
        return redirect('core:manage_reviews')

    return render(request, 'core/instructor_manage_reviews.html', {'reviews': reviews})


@login_required
def complete_course(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    enrollment = Enrollment.objects.filter(user=request.user, course=course).first()

    if enrollment:
        enrollment.completed = True
        enrollment.save()
        messages.success(request, f"🎉 तू '{course.title}' कोर्स पूर्ण केला आहेस!")
    else:
        messages.error(request, "तू या कोर्समध्ये enrolled नाहीस!")

    return redirect('core:course_detail', slug=course.slug)


@login_required
def add_quiz(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    if request.method == 'POST':
        title = request.POST['title']
        description = request.POST['description']
        total_marks = request.POST['total_marks']
        Quiz.objects.create(course=course, title=title, description=description, total_marks=total_marks)
        return redirect('core:instructor_dashboard')
    return render(request, 'core/add_quiz.html', {'course': course})
@login_required
def add_assignment(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')
        due_date = request.POST.get('due_date')
        Assignment.objects.create(course=course, title=title, description=description, due_date=due_date)
        messages.success(request, 'Assignment added successfully!')
        return redirect('core:instructor_dashboard')
    return render(request, 'core/add_assignment.html', {'course': course})

@login_required
def manage_assignments(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    assignments = Assignment.objects.filter(course=course)
    return render(request, 'core/manage_assignments.html', {'course': course, 'assignments': assignments})

@login_required
def edit_assignment(request, assignment_id):
    assignment = get_object_or_404(Assignment, id=assignment_id)
    if request.method == 'POST':
        assignment.title = request.POST.get('title')
        assignment.description = request.POST.get('description')
        assignment.deadline = request.POST.get('deadline')
        assignment.save()
        messages.success(request, 'Assignment updated successfully!')
        return redirect('core:manage_assignments', course_id=assignment.course.id)
    return render(request, 'core/edit_assignment.html', {'assignment': assignment})

@login_required
def delete_assignment(request, assignment_id):
    assignment = get_object_or_404(Assignment, id=assignment_id)
    course_id = assignment.course.id
    assignment.delete()
    messages.success(request, 'Assignment deleted successfully!')
    return redirect('core:manage_assignments', course_id=course_id)


@login_required
def submit_assignment(request, assignment_id):
    assignment = get_object_or_404(Assignment, id=assignment_id)
    if request.method == 'POST' and request.FILES.get('file'):
        file = request.FILES['file']
        Submission.objects.create(
            assignment=assignment,
            user=request.user,
            submitted_file=file
        )
        messages.success(request, "Assignment submitted successfully!")
        return redirect('core:course_content', course_id=assignment.course.id)
    return render(request, 'core/submit_assignment.html', {'assignment': assignment})

@login_required
def grade_submission(request, submission_id):
    submission = get_object_or_404(Submission, id=submission_id)

    if request.method == 'POST':
        submission.grade = request.POST.get('grade')
        submission.feedback = request.POST.get('feedback')
        submission.save()
        messages.success(request, "Grade assigned successfully!")
        return redirect('core:manage_assignments', course_id=submission.assignment.course.id)

    return render(request, 'core/grade_submission.html', {'submission': submission})



# ------- start_quiz / quiz_detail already OK but ensure redirect uses namespaced name -------
@login_required
def start_quiz(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id)
    questions = quiz.questions.all()

    if request.method == "POST":
        correct_count = 0
        for q in questions:
            selected = request.POST.get(str(q.id))
            if selected and int(selected) == q.correct_option:
                correct_count += 1

        attempt = QuizAttempt.objects.create(
            quiz=quiz,
            user=request.user,
            total_questions=questions.count(),
            correct_answers=correct_count,
            score=(correct_count / questions.count()) * 100 if questions.count() > 0 else 0,
            completed=True
        )
        return redirect('core:quiz_result', attempt_id=attempt.id)

    return render(request, 'core/start_quiz.html', {'quiz': quiz, 'questions': questions})


@login_required
def quiz_result(request, attempt_id):
    attempt = get_object_or_404(QuizAttempt, id=attempt_id, user=request.user)
    total = attempt.quiz.questions.count()
    percentage = (attempt.score / total) * 100 if total > 0 else 0
    return render(request, 'core/quiz_result.html', {
        'attempt': attempt,
        'percentage': percentage
    })


@staff_member_required
def manage_payments(request):
    """Admin / instructor panel to approve or reject payments."""
    enrollments = Enrollment.objects.all().order_by('-created_at')

    if request.method == 'POST':
        eid = request.POST.get('enrollment_id')
        action = request.POST.get('action')
        enrollment = get_object_or_404(Enrollment, id=eid)

        if action == 'approve':
            enrollment.approved = True
            enrollment.approved_on = timezone.now()
            enrollment.save()

            # Send approval email
            send_mail(
                subject="🎉 Payment Approved - Access Granted",
                message=f"Hi {enrollment.user.username},\n\nYour payment for '{enrollment.course.title}' has been approved! You now have full access.",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[enrollment.user.email],
                fail_silently=True,
            )

            messages.success(request, f"{enrollment.user.username}'s payment approved successfully.")

        elif action == 'reject':
            enrollment.delete()
            messages.warning(request, "Payment request rejected and removed.")

        return redirect('core:manage_payments')

    return render(request, 'core/manage_payments.html', {'enrollments': enrollments})

# ------- Add Quiz (robust to model shape and form input names) -------

@login_required
def add_quiz(request, course_id):
    course = get_object_or_404(Course, id=course_id)

    if request.method == "POST":
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()

        if not title:
            messages.error(request, "Quiz title cannot be empty.")
            return redirect('core:add_quiz', course_id=course.id)

        # Create quiz
        quiz = Quiz.objects.create(
            title=title,
            description=description,
            course=course
        )

        # Get all dynamic question data
        questions = request.POST.getlist('question_text[]')
        option1_list = request.POST.getlist('option1[]')
        option2_list = request.POST.getlist('option2[]')
        option3_list = request.POST.getlist('option3[]')
        option4_list = request.POST.getlist('option4[]')
        correct_options = request.POST.getlist('correct_option[]')
        marks_list = request.POST.getlist('marks[]')

        # No questions? Delete quiz
        if not questions:
            messages.error(request, "Add at least one question.")
            quiz.delete()
            return redirect('core:add_quiz', course_id=course.id)

        # Function to convert values safely
        def safe_int(val):
            try:
                return int(val)
            except:
                return None

        # Create each question
        for i in range(len(questions)):
            q_text = questions[i].strip()
            opt1 = option1_list[i].strip()
            opt2 = option2_list[i].strip()
            opt3 = option3_list[i].strip()
            opt4 = option4_list[i].strip()
            correct_opt = safe_int(correct_options[i])
            marks = safe_int(marks_list[i]) or 1

            # Validation per question
            if not q_text or not opt1 or not opt2 or not opt3 or not opt4 or not correct_opt:
                continue  # skip empty question row

            # Save question
            Question.objects.create(
                quiz=quiz,
                text=q_text,
                option1=opt1,
                option2=opt2,
                option3=opt3,
                option4=opt4,
                correct_option=correct_opt,
                marks=marks
            )

        messages.success(request, "Quiz created successfully!")
        return redirect('core:instructor_dashboard')

    return render(request, 'core/add_quiz.html', {'course': course})



# Manage Quiz
def manage_quizzes(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    quizzes = Quiz.objects.filter(course=course)

    return render(request, 'core/manage_quizzes.html', {
        'course': course,
        'quizzes': quizzes,
    })


# Edit Quiz
@login_required
def edit_quiz(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id, course__instructor=request.user)
    if request.method == 'POST':
        quiz.title = request.POST['title']
        quiz.description = request.POST.get('description', '')
        quiz.total_marks = request.POST['total_marks']
        quiz.save()
        messages.success(request, "Quiz updated successfully!")
        return redirect('core:manage_quizzes')
    return render(request, 'core/edit_quiz.html', {'quiz': quiz})


# Delete Quiz
@login_required
def delete_quiz(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id, course__instructor=request.user)
    quiz.delete()
    messages.success(request, "Quiz deleted successfully!")
    return redirect('core:manage_quizzes')

# ------- Add single question view (ensures numeric correct_option) -------
@login_required
def add_question(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id)
    if request.method == 'POST':
        question_text = request.POST.get('question_text', '').strip()
        # allow both naming styles
        option1 = request.POST.get('option1') or request.POST.get('option_a') or ''
        option2 = request.POST.get('option2') or request.POST.get('option_b') or ''
        option3 = request.POST.get('option3') or request.POST.get('option_c') or ''
        option4 = request.POST.get('option4') or request.POST.get('option_d') or ''
        correct_raw = request.POST.get('correct_option') or ''

        # convert A/B/C/D -> 1..4
        mapping = {'A':1,'B':2,'C':3,'D':4,'a':1,'b':2,'c':3,'d':4}
        correct = mapping.get(correct_raw, None)
        if correct is None:
            try:
                correct = int(correct_raw)
            except (TypeError, ValueError):
                correct = None

        if not (question_text and option1 and option2 and option3 and option4 and correct in (1,2,3,4)):
            messages.error(request, "Please provide complete question data and a valid correct option (1-4 or A-D).")
            return redirect('core:add_question', quiz_id=quiz.id)

        Question.objects.create(
            quiz=quiz,
            question_text=question_text,
            option1=option1,
            option2=option2,
            option3=option3,
            option4=option4,
            correct_option=correct
        )
        messages.success(request, "Question added.")
        return redirect('core:view_quiz_questions', quiz_id=quiz.id)

    return render(request, 'core/add_question.html', {'quiz': quiz})


def view_quiz_questions(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id)
    questions = quiz.questions.all()

    return render(request, 'core/view_quiz_questions.html', {
        'quiz': quiz,
        'questions': questions
    })

@login_required
def edit_question(request, question_id):
    question = get_object_or_404(Question, id=question_id)

    if request.method == 'POST':
        question.question_text = request.POST.get('question_text')
        question.option1 = request.POST.get('option1')
        question.option2 = request.POST.get('option2')
        question.option3 = request.POST.get('option3')
        question.option4 = request.POST.get('option4')
        question.correct_option = request.POST.get('correct_option')
        question.save()
        messages.success(request, 'Question updated successfully!')
        return redirect('core:view_quiz_questions', quiz_id=question.quiz.id)

    return render(request, 'core/edit_question.html', {'question': question})

# ------- Delete question (fixed variable usage and redirect name) -------
@login_required
def delete_question(request, question_id):
    question = get_object_or_404(Question, id=question_id)
    quiz_id = question.quiz.id
    question.delete()
    messages.success(request, "Question deleted successfully.")
    # Use namespaced url name consistent with your urls: 'core:view_quiz_questions'
    return redirect('core:view_quiz_questions', quiz_id=quiz_id)


@login_required(login_url='core:login')
def approve_certificate(request, enrollment_id):
    """Instructor approves a student's certificate."""
    enrollment = get_object_or_404(Enrollment, id=enrollment_id)
    if request.user == enrollment.course.instructor:
        enrollment.certificate_approved = True
        enrollment.certificate_generated_on = timezone.now()
        enrollment.save()
        messages.success(request, f"Certificate approved for {enrollment.user.username}.")
    else:
        messages.error(request, "You are not authorized to approve this certificate.")
    return redirect('core:course_content', course_id=enrollment.course.id)

@login_required
def submit_quiz(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id)
    questions = Question.objects.filter(quiz=quiz)


    score = 0
    total = quiz.total_marks


    for q in questions:
        selected = request.POST.get(str(q.id))
    if selected and selected == q.correct_option:
        score += q.marks


    percentage = (score / total) * 100


    grade = ""
    if percentage >= 90:
            grade = "A+"
    elif percentage >= 80:
            grade = "A"
    elif percentage >= 70:
            grade = "B+"
    elif percentage >= 60:
                grade = "B"
    elif percentage >= 50:
            grade = "C"
    else:
            grade = "Fail"


    CompletedQuiz.objects.create(
    student=request.user,
    quiz=quiz,
    score=percentage
    )


    return render(request, 'student/quiz_result.html', {
    'quiz': quiz,
    'score': score,
    'total': total,
    'percentage': percentage,
    'grade': grade
    })

@login_required
def download_certificate(request, slug):
    course = get_object_or_404(Course, slug=slug)
    enrollment = get_object_or_404(Enrollment, course=course, user=request.user)

    if not enrollment.certificate_approved or not enrollment.certificate_generated_on:
        return HttpResponse("Certificate not approved yet.")

    # Create PDF
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{course.title}_certificate.pdf"'

    p = canvas.Canvas(response)
    width, height = 595, 842  # A4 size

    p.setFont("Helvetica-Bold", 24)
    p.drawCentredString(width / 2, height - 150, "Certificate of Completion")

    p.setFont("Helvetica", 16)
    p.drawCentredString(width / 2, height - 200, "This is to certify that")
    p.setFont("Helvetica-Bold", 20)
    p.drawCentredString(width / 2, height - 240, enrollment.user.get_full_name() or enrollment.user.username)
    p.setFont("Helvetica", 16)
    p.drawCentredString(width / 2, height - 280, "has successfully completed the course")
    p.setFont("Helvetica-Bold", 18)
    p.drawCentredString(width / 2, height - 320, course.title)

    # Certificate date
    p.setFont("Helvetica", 12)
    p.drawCentredString(
        width / 2,
        height - 370,
        f"Date: {enrollment.certificate_generated_on.strftime('%b %d, %Y')}"
    )

    p.showPage()
    p.save()
    return response


@login_required
def course_content(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    enrolled = Enrollment.objects.filter(course=course, user=request.user).exists()

    if not enrolled:
        messages.error(request, "You need to purchase this course first!")
        return redirect('core:course_detail', slug=course.slug)

    user_submissions = Submission.objects.filter(
    user=request.user,
    assignment__course=course
    )


    modules = Module.objects.filter(course=course)
    # ✅ FIXED: access lessons via module’s relation
    lessons = Lesson.objects.filter(module__course=course)
    quizzes = Quiz.objects.filter(course=course)
    assignments = Assignment.objects.filter(course=course)

    return render(request, 'core/course_content.html', {
        'course': course,
        'modules': modules,
        'lessons': lessons,
        'quizzes': quizzes,
        'assignments': assignments,
        'user_submissions': user_submissions,  
    })


@login_required
def grade_submissions(request):
    # ✅ Only instructors can access this
    if not request.user.is_staff:
        messages.error(request, "You are not authorized to view this page.")
        return redirect('core:home')

    submissions = Submission.objects.select_related('assignment', 'user').order_by('-submitted_at')

    if request.method == 'POST':
        submission_id = request.POST.get('submission_id')
        grade = request.POST.get('grade')
        feedback = request.POST.get('feedback')

        sub = get_object_or_404(Submission, id=submission_id)
        sub.grade = grade
        sub.feedback = feedback
        sub.graded_by = request.user
        sub.graded_at = timezone.now()
        sub.save()

        messages.success(request, f"✅ Grade saved for {sub.user.username}'s submission.")
        return redirect('core:grade_submissions')

    return render(request, 'core/grade_submissions.html', {'submissions': submissions})



@login_required
def profile(request):
    return render(request, "core/profile.html", {
        "user": request.user,
    })




@login_required
def edit_profile(request):
    user = request.user

    if request.method == "POST":
        username = request.POST.get('username')
        email = request.POST.get('email')
        is_instructor = request.POST.get('is_instructor') == 'True'
        avatar = request.FILES.get('avatar')

        user.username = username
        user.email = email
        user.save()

        profile = user.profile
        profile.is_instructor = is_instructor
        if avatar:
            profile.avatar = avatar
        profile.save()

        messages.success(request, "Profile updated successfully!")
        return redirect('core:profile')

    return render(request, 'core/edit_profile.html', {'user': user})


def about(request):
    team = User.objects.filter(is_staff=True)  # All staff (admin + instructors)
    return render(request, 'core/about.html', {'team': team})

def faqs_page(request):
    return render(request, 'core/faqs.html')

def support_page(request):
    return render(request, 'core/support.html')


def support_view(request):
    if request.method == "POST":
        form = SupportForm(request.POST)
        if form.is_valid():
            # Save to database
            SupportMessage.objects.create(
                name=form.cleaned_data['name'],
                email=form.cleaned_data['email'],
                subject=form.cleaned_data['subject'],
                message=form.cleaned_data['message'],
            )

            # Send email notification (optional)
            send_mail(
                subject=f"Support Request: {form.cleaned_data['subject']}",
                message=f"From: {form.cleaned_data['name']} <{form.cleaned_data['email']}>\n\nMessage:\n{form.cleaned_data['message']}",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=['support@techkida.com'],  # admin email
            )

            messages.success(request, "✅ Your message has been sent successfully! We'll contact you soon.")
            return redirect('support')
    else:
        form = SupportForm()

    return render(request, 'core/support.html', {'form': form})



@login_required
def update_instructor_profile(request):
    if request.method == 'POST':
        profile = request.user.profile
        profile.specialization = request.POST.get('specialization', '')
        profile.experience = request.POST.get('experience', 0)
        profile.bio = request.POST.get('bio', '')
        profile.save()
        messages.success(request, "Instructor profile updated successfully!")
    return redirect('core:profile')

def quiz_detail(request, quiz_id):
    quiz = Quiz.objects.get(id=quiz_id)
    questions = quiz.questions.all()

    if request.method == 'POST':
        correct_count = 0
        for q in questions:
            selected_option = request.POST.get(str(q.id))
            if selected_option and int(selected_option) == q.correct_option:
                correct_count += 1

        attempt = QuizAttempt.objects.create(
            quiz=quiz,
            user=request.user,
            total_questions=questions.count(),
            correct_answers=correct_count,
            score=(correct_count / questions.count()) * 100,
            completed=True
        )
        return redirect('core:quiz_result', attempt_id=attempt.id)

    return render(request, 'core/quiz_detail.html', {'quiz': quiz, 'questions': questions})

@login_required
def view_quiz_submission(request, attempt_id):
    attempt = get_object_or_404(QuizAttempt, id=attempt_id)
    questions = attempt.quiz.questions.all()

    # Collect user's answers if stored somewhere (optional)
    return render(request, 'core/view_quiz_submission.html', {
        'attempt': attempt,
        'questions': questions,
    })

def calculate_score(self):
    correct_count = 0
    total_questions = self.quiz.questions.count()
    
    for ans in self.answers.all():
        if ans.selected_option == ans.question.correct_option:
            correct_count += 1
    
    self.correct_answers = correct_count
    self.total_questions = total_questions
    self.score = correct_count  # Or apply per-question marks
    self.mark_completed()
@login_required
def edit_lesson(request, lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id)

    if request.method == "POST":
        lesson.title = request.POST.get("title")
        lesson.description = request.POST.get("description")
        lesson.content = request.POST.get("content")  # ✅ Added this line
        lesson.video_url = request.POST.get("video_url")
        lesson.save()

        messages.success(request, "Lesson updated successfully!")
        return redirect("instructor_dashboard")  # ✅ Make sure this name exists

    return render(request, "core/edit_lesson.html", {"lesson": lesson})

@login_required
def confirm_payment(request, course_id):
    course = get_object_or_404(Course, id=course_id)

    if request.method == 'POST':
        transaction_id = request.POST.get('transaction_id')
        mobile = request.POST.get('mobile')

        Payment.objects.create(
            user=request.user,
            course=course,
            transaction_id=transaction_id,
            mobile=mobile,
            amount=course.price,
            approved=False  # admin will approve later
        )
        messages.success(request, 'Payment submitted! Waiting for admin approval.')
        return redirect('core:course_detail', slug=course.slug)

    return render(request, 'core/confirm_payment.html', {'course': course})

def payment_success(request, course_id):
    """
    Show payment success message after the user completes payment.
    """
    course = get_object_or_404(Course, id=course_id)
    context = {
        'course': course,
    }
    return render(request, 'core/payment_success.html', context)

@login_required(login_url='core:login')
def review_page(request, course_id):
    course = get_object_or_404(Course, id=course_id)

    # Check enrollment
    enrolled = Enrollment.objects.filter(user=request.user, course=course).first()
    if not enrolled:
        messages.warning(request, "You must be enrolled in the course to leave a review.")
        return redirect('core:course_detail', slug=course.slug)

    # Handle review submission
    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            if Review.objects.filter(course=course, user=request.user).exists():
                messages.warning(request, "You have already submitted a review for this course.")
                return redirect('core:review_page', course_id=course.id)

            review = form.save(commit=False)
            review.course = course
            review.user = request.user
            review.save()

            messages.success(request, "Your review has been submitted successfully!")
            return redirect('core:review_page', course_id=course.id)
    else:
        form = ReviewForm()

    reviews = course.reviews.order_by('-created_at')

    return render(request, 'core/review_page.html', {
        'course': course,
        'reviews': reviews,
        'form': form,
        'enrolled': enrolled,
    })

@login_required
def approve_review(request, review_id):
    review = get_object_or_404(Review, id=review_id)
    review.approved = True
    review.save()
    messages.success(request, "Review approved successfully!")
    return redirect('core:manage_feedbacks')  # or instructor dashboard


@login_required
def delete_review(request, review_id):
    review = get_object_or_404(Review, id=review_id)
    review.delete()
    messages.success(request, "Review deleted successfully.")
    return redirect('core:manage_feedbacks')   # or wherever you manage reviews
@login_required
def view_quiz_attempts(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id)

    attempts = CompletedQuiz.objects.filter(quiz=quiz).select_related("student")

    return render(request, "core/view_quiz_attempts.html", {
        "quiz": quiz,
        "attempts": attempts,
    })

