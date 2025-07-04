from django.utils import timezone
from typing import List
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from ninja import NinjaAPI
from lms_core.schema import (
    ApproveCommentRequest, BookmarkOut, CategoryIn, CompletionOut, CompletionTrackingCreateSchema, CompletionTrackingResponseSchema, ContentOut, ContentUpdateSchema, CourseAnalyticsOut, CourseContentIn, CourseSchemaOut, CourseMemberOut, CourseSchemaIn,
    CourseContentMini, CourseContentFull,
    CourseCommentOut, CourseCommentIn, EnrollStudentIn, EnrollStudentOut, FeedbackIn, FeedbackOut,
    RegisterIn, CourseAddIn, UserProfileOut
)
from ninja.errors import HttpError
from lms_core.models import Category, CompletionTracking, ContentBookmark, ContentCompletion, Course, CourseFeedback, CourseMember, CourseContent, Comment
from django.contrib.auth.models import AnonymousUser
from ninja_simple_jwt.auth.views.api import mobile_auth_router
from ninja_simple_jwt.auth.ninja_auth import HttpJwtAuth
from django.contrib.auth.models import User
from django.contrib.auth import get_user_model
from lms_core.custom_jwt import CustomJWTAuth
from ninja.responses import Response
from lms_core.models import CourseContent, Comment, Course,Announcement
from lms_core.schema import CourseCommentOut
from ninja import Schema
from typing import List
from ninja.throttling import AnonRateThrottle, AuthRateThrottle
from lms_core.throttles import CommentThrottle, CourseCreateThrottle, RegisterThrottle
from lms_core.throttles import ContentCreateThrottle
from lms_core.schema import AnnouncementIn,CategoryOut
from lms_core.models import Course, Announcement, CourseMember
from lms_core.schema import AnnouncementOut
from typing import List
from ninja.errors import AuthenticationError


apiv1 =  NinjaAPI(
    throttle=[
        AnonRateThrottle("10/s"),        # Untuk unauthenticated
        AuthRateThrottle("100/s"),       # Untuk authenticated
    ])
apiv1.add_router("/auth/", mobile_auth_router)
apiAuth = HttpJwtAuth()


@apiv1.post("/auth/register",throttle=RegisterThrottle(), response={201: dict, 400: dict})
def register_user(request, data: RegisterIn):
    if User.objects.filter(username=data.username).exists():
        return 400, {"error": "Username sudah digunakan"}
    if User.objects.filter(email=data.email).exists():
        return 400, {"error": "Email sudah digunakan"}

    user = User.objects.create_user(
        username=data.username,
        password=data.password,
        email=data.email,
        first_name=data.first_name,
        last_name=data.last_name
    )

    return 201, {"message": "Pendaftaran berhasil", "user_id": user.id}


@apiv1.post("/course/add",throttle=CourseCreateThrottle(), auth=apiAuth, response=CourseSchemaOut)
def add_course(request, data: CourseAddIn):
    user = request.user
    course = Course.objects.create(
        name=data.name,
        description=data.description,
        price=data.price,
        teacher=User.objects.get(id=data.teacher_id) if data.teacher_id else user
    )
    return CourseSchemaOut.from_orm(course)


@apiv1.get("/mycourses", auth=apiAuth, response=list[CourseMemberOut])
def my_courses(request):
    user = User.objects.get(id=request.user.id)
    courses = CourseMember.objects.select_related('user_id', 'course_id').filter(user_id=user)
    return courses

# @apiv1.post("/courses/{course_id}/enroll", auth=apiAuth, response=CourseMemberOut)
# def enroll_course(request, course_id: int):
#     user = request.user.id
#     member = 17
#     try:
#         course = Course.objects.get(id=course_id)
#     except Course.DoesNotExist:
#         return 404, {"error": "Course not found"}
#     if course.teacher_id != user:
#         return 403, {"error": "You are not allowed to enroll in this course"}
#     course_member = CourseMember(course_id=course, user_id=member, roles="std")
#     course_member.save()
#     return course_member

@apiv1.post("/courses/{course_id}/enroll", auth=apiAuth, response={201: dict, 403: dict, 404: dict})
def enroll_course(request, course_id: int, data: EnrollStudentIn):
    user_id = request.user.id

    try:
        course = Course.objects.get(id=course_id)
    except Course.DoesNotExist:
        return 404, {"error": "Course not found"}

    if course.teacher_id != user_id:
        return 403, {"error": "You cannot enroll in this course"}

    enrolled = []
    skipped = []

    for student_id in data.user_id:
        student_target = User.objects.get(id=student_id)
        if CourseMember.objects.filter(course_id=course, user_id=student_target).exists():
            skipped.append(student_id)
            continue

        CourseMember.objects.create(
            course_id=course,
            user_id=student_target,
            roles=data.role
        )
        enrolled.append(student_id)

    return 201, {
        "message": "Enrollment completed",
    }


@apiv1.post("/contents/{content_id}/comments",throttle=CommentThrottle(), auth=apiAuth, response={201: CourseCommentOut})
def create_content_comment(request, content_id: int, data: CourseCommentIn):
    user = User.objects.get(id=request.user.id)
    content = CourseContent.objects.get(id=content_id)

    if not content.course_id.is_member(user):
        message =  {"error": "You are not authorized to create comment in this content"}
        return Response(message, status=401)
    
    member = CourseMember.objects.get(course_id=content.course_id, user_id=user)
    
    comment = Comment.objects.create(
        content_id=content,
        member_id=member,
        comment=data.comment
    )
    comment.save()
    return 201, comment



@apiv1.put(
    "/contents/{content_id}/comments/moderate",
    auth=apiAuth,
    response={200: List[CourseCommentOut], 403: dict, 404: dict}
)
def approve_comments(request, content_id: int, data: ApproveCommentRequest):
    user_id = request.user.id

    try:
        content = CourseContent.objects.select_related("course_id").get(id=content_id)
    except CourseContent.DoesNotExist:
        return 404, {"error": "Content not found"}

    if content.course_id.teacher_id != user_id:
        return 403, {"error": "You are not authorized to moderate comments for this content."}

    Comment.objects.filter(
        id__in=data.comment_ids,
        content_id=content
    ).update(is_approved=True)

    approved_comments = Comment.objects.filter(
        id__in=data.comment_ids,
        content_id=content,
        is_approved=True
    ).select_related("member_id", "member_id__user_id", "content_id", "content_id__course_id")

    return list(approved_comments)

@apiv1.get("/courses/{course_id}/contents", response=list[CourseContentMini])
def list_content_course(request, course_id: int):
    contents = CourseContent.objects.filter(course_id=course_id)
    return contents


@apiv1.post(
    "/courses/{course_id}/contents",throttle=ContentCreateThrottle(),
    auth=apiAuth,
    response={201: dict, 403: dict}
)
def add_content_course(request, course_id: int, data: CourseContentIn):
    user = request.user.id
    course = Course.objects.get(id=course_id)

    if course.teacher_id != user:
        return 403, {"error": "You are not allowed to add content in this course"}

    content = CourseContent.objects.create(
        name=data.name,
        description=data.description,
        course_id=course 
    )
    return 201, {"message": "successfully add content"}

@apiv1.post("/courses/{course_id}/announcements", auth=apiAuth,response={201:dict,403:dict})
def create_annoncement(request, course_id:int, data: AnnouncementIn):
    user = request.user.id
    course = Course.objects.get(id=course_id)
    if course.teacher_id != user:
        return 403, {"error": "You are not allowed because you are not the teacher of this course"}
    
    announcement = Announcement.objects.create (
        title=data.title,
        content=data.content,
        course=course,
        start_date=data.start_date,
        end_date=data.end_date,
        created_by=get_user_model().objects.get(id=user),
    )
    announcement.save()
    return 201, {"message": "Announcement created successfully", "announcement_id": announcement.id}



@apiv1.get(
    "/courses/{course_id}/announcements",auth=apiAuth,
    response={200: List[AnnouncementOut], 404: dict}
)
def list_announcements(request, course_id: int):

    user = getattr(request, "auth", None)
    print (f"User: {user}")
    announcements = Announcement.objects.filter(course_id=course_id)
    return list(announcements)

@apiv1.put(
    "/courses/{course_id}/announcements/{announcement_id}",
    auth=apiAuth,
    response={200: AnnouncementOut, 403: dict, 404: dict}
)
def update_announcement(request, course_id: int, announcement_id: int, data: AnnouncementIn):
    user = request.user.id

    # Cek apakah course ada
    try:
        course = Course.objects.get(id=course_id)
    except Course.DoesNotExist:
        return 404, {"error": "Course not found"}

    # Hanya teacher dari course tersebut yang boleh edit
    if course.teacher_id != user:
        return 403, {"error": "You are not allowed to update this announcement"}

    # Cek apakah announcement milik course tersebut
    try:
        announcement = Announcement.objects.get(id=announcement_id, course_id=course_id)
    except Announcement.DoesNotExist:
        return 404, {"error": "Announcement not found"}

    # Update datanya
    announcement.title = data.title
    announcement.content = data.content
    announcement.start_date = data.start_date
    announcement.end_date = data.end_date
    announcement.save()

    return 200, announcement

@apiv1.delete(
    "/courses/{course_id}/announcements/{announcement_id}",
    auth=apiAuth,
    response={200: dict, 403: dict, 404: dict}
)
def delete_announcement(request, course_id: int, announcement_id: int):
    user_id = request.user.id

    try:
        course = Course.objects.get(id=course_id)
    except Course.DoesNotExist:
        return 404, {"error": "Course not found"}

    if course.teacher_id != user_id:
        return 403, {"error": "You are not allowed to delete this announcement"}

    try:
        announcement = Announcement.objects.get(id=announcement_id, course_id=course_id)
    except Announcement.DoesNotExist:
        return 404, {"error": "Announcement not found"}

    announcement.delete()
    return 200, {"message": "Announcement deleted successfully"}


@apiv1.post("/courses/{course_id}/bookmark", auth=apiAuth, response={201: dict, 403: dict, 404: dict})
def bookmark_course(request, course_id: int):
    user = request.user
    try:
        course = Course.objects.get(id=course_id)
    except Course.DoesNotExist:
        return 404, {"error": "Course not found"}

    if not course.is_member(user):
        return 403, {"error": "You are not authorized to bookmark this course"}

    if user in course.bookmarked_by.all():
        return 400, {"error": "You have already bookmarked this course"}

    course.bookmarked_by.add(user)
    return 201, {"message": "Course bookmarked successfully"}

@apiv1.post("/content/{content_id}/bookmark", auth=apiAuth, response={200: dict, 401: dict})
def add_bookmark(request, content_id: int):
    user = request.user.id

    try:
        content = CourseContent.objects.get(id=content_id)
    except CourseContent.DoesNotExist:
        return 400, {"error": "Content not found"}

    bookmark, created = ContentBookmark.objects.get_or_create(
        content=content,
        user=user  # Jika pakai ForeignKey
    )

    return {"message": "Bookmark added", "bookmark_id": bookmark.id}

@apiv1.get("/bookmark", response={200: list[BookmarkOut], 401: dict})
def get_bookmarks(request):
    user = request.user
    if not user.is_authenticated:
        return 401, {"detail": "Unauthorized"}

    bookmarks = ContentBookmark.objects.select_related("content__course_id").filter(user=user)
    return 200, bookmarks

@apiv1.put("/content/{content_id}", auth=apiAuth, response={200: dict, 403: dict, 404: dict})
def update_content(request, content_id: int, data: ContentUpdateSchema):
    user = request.user

    try:
        content = CourseContent.objects.select_related('course_id').get(id=content_id)
    except CourseContent.DoesNotExist:
        return 404, {"detail": "Content not found"}

    if content.course_id.teacher_id != user.id:
        return 403, {"detail": "You are not the teacher of this course"}

    for attr, value in data.dict(exclude_none=True).items():
        setattr(content, attr, value)
    content.save()

    return {"detail": "Content updated successfully"}


@apiv1.get("/course/{course_id}/contents", response=list[ContentOut])
def get_course_contents(request, course_id: int):
    user = request.user.id
    course = Course.objects.get(id=course_id)

    queryset = CourseContent.objects.select_related("course_id").filter(course_id=course)

    if course.teacher_id != user:
        queryset = queryset.filter(is_published=True)

    return queryset

@apiv1.post("/add-completion/", auth=apiAuth)
def add_completion_tracking(request, data: CompletionTrackingCreateSchema):
    student_username = data.student_username  
    try:
        student = User.objects.get(username=student_username)
    except User.DoesNotExist:
        return JsonResponse({"detail": "User not found"}, status=404)

    content = get_object_or_404(CourseContent, id=data.content_id)

    completion, created = CompletionTracking.objects.update_or_create(
        student=student,
        content=content,
        defaults={'completed': True, 'completed_at': timezone.now()}
    )

    return JsonResponse({
        "student_username": student.username,
        "content_id": content.id,
        "completed": completion.completed,
        "completed_at": completion.completed_at,
    }, status=200)


@apiv1.get("/show-completion/", auth=apiAuth, response=CompletionTrackingResponseSchema)
def show_completion(request, course_id: int):
    course = get_object_or_404(Course, id=course_id)
    course_contents = CourseContent.objects.filter(course_id=course.id)

    completions = CompletionTracking.objects.filter(content__in=course_contents)

    completion_data = []
    for completion in completions:
        completion_data.append({
            "student_id": completion.student.id,
            "student_username": completion.student.username,
            "content_id": completion.content.id,
            "content_name": completion.content.name,
            "completed": completion.completed,
            "completed_at": completion.completed_at,
        })

    return JsonResponse({
        "course_id": course.id,
        "completions": completion_data
    }, status=200)


@apiv1.delete("/delete-completion/", auth=apiAuth)
def delete_completion(request, student_id: int, content_id: int):
    student = get_object_or_404(User, id=student_id)
    
    completion = CompletionTracking.objects.filter(student=student, content_id=content_id).first()
    
    if not completion:
        return JsonResponse({"error": "Completion not found for this student and content."}, status=404)

    completion.delete()
    
    return JsonResponse({"message": "Completion successfully deleted."}, status=200)