from ninja import NinjaAPI
from lms_core.schema import (
    CourseSchemaOut, CourseMemberOut, CourseSchemaIn,
    CourseContentMini, CourseContentFull,
    CourseCommentOut, CourseCommentIn,
    RegisterIn, RegisterOut, BatchEnrollIn, CourseAddIn
)
from lms_core.models import Course, CourseMember, CourseContent, Comment
from ninja_simple_jwt.auth.views.api import mobile_auth_router
from ninja_simple_jwt.auth.ninja_auth import HttpJwtAuth
from django.contrib.auth.models import User
from django.contrib.auth import get_user_model

User = get_user_model()  # tetap gunakan User bawaan

apiv1 = NinjaAPI()
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


@apiv1.post("/course/batch-enroll", response={200: dict, 403: dict, 404: dict}, auth=apiAuth)
def batch_enroll_students(request, data: BatchEnrollIn):
    user = request.user

    try:
        course = Course.objects.get(id=data.course_id)
    except Course.DoesNotExist:
        return 404, {"error": "Course tidak ditemukan"}

    if course.teacher != user:
        return 403, {"error": "Anda tidak memiliki akses ke kursus ini"}

    enrolled = []
    skipped = []

    for student in data.students:
        try:
            target_user = User.objects.get(id=student.user_id)
        except User.DoesNotExist:
            skipped.append(student.user_id)
            continue

        exists = CourseMember.objects.filter(course=course, user=target_user).exists()
        if not exists:
            CourseMember.objects.create(
                course=course,
                user=target_user,
                roles=student.role
            )
            enrolled.append(student.user_id)
        else:
            skipped.append(student.user_id)

    return 200, {
        "success": True,
        "enrolled": enrolled,
        "skipped": skipped
    }
