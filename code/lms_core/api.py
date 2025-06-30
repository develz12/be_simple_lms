from typing import List
from django.shortcuts import get_object_or_404
from ninja import NinjaAPI
from lms_core.schema import (
    ApproveCommentRequest, CourseSchemaOut, CourseMemberOut, CourseSchemaIn,
    CourseContentMini, CourseContentFull,
    CourseCommentOut, CourseCommentIn, EnrollStudentIn,
    RegisterIn, CourseAddIn, EnrollStudentOut
)
from lms_core.models import Course, CourseMember, CourseContent, Comment
from ninja_simple_jwt.auth.views.api import mobile_auth_router
from ninja_simple_jwt.auth.ninja_auth import HttpJwtAuth
from django.contrib.auth.models import User
from django.contrib.auth import get_user_model
from lms_core.custom_jwt import CustomJWTAuth
from ninja_jwt.authentication import JWTAuth
from ninja.responses import Response
from lms_core.models import CourseContent, Comment, Course
from lms_core.schema import CourseCommentOut
from ninja import Schema
from typing import List
from ninja.throttling import AnonRateThrottle, AuthRateThrottle


apiv1 =  NinjaAPI(
    throttle=[
        AnonRateThrottle("10/s"),        # Untuk unauthenticated
        AuthRateThrottle("100/s"),       # Untuk authenticated
    ])
apiv1.add_router("/auth/", mobile_auth_router)
apiAuth = HttpJwtAuth()


@apiv1.post("/auth/register", response={201: dict, 400: dict})
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


@apiv1.post("/course/add", auth=apiAuth, response=CourseSchemaOut)
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


@apiv1.post("/contents/{content_id}/comments", auth=apiAuth, response={201: CourseCommentOut})
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

    # Ambil kembali yang sudah disetujui
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