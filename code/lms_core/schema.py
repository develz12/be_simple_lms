from ninja import Schema
from typing import Literal, Optional,List
from datetime import datetime
from pydantic import BaseModel
from typing import List

from django.contrib.auth.models import User

class UserOut(Schema):
    id: int
    email: str
    first_name: str
    last_name: str


class CourseSchemaOut(Schema):
    id: int
    name: str
    description: str
    price: int
    image : Optional[str]
    teacher: UserOut
    created_at: datetime
    updated_at: datetime

class CourseMemberOut(Schema):
    id: int 
    course_id: CourseSchemaOut
    user_id: UserOut
    roles: str
    # created_at: datetime

    # class Config:
    #     orm_mode = True


class CourseSchemaIn(Schema):
    name: str
    description: str
    price: int


class CourseContentMini(Schema):
    id: int
    name: str
    description: str
    course_id: CourseSchemaOut
    created_at: datetime
    updated_at: datetime


class CourseContentFull(Schema):
    id: int
    name: str
    description: str
    video_url: Optional[str]
    file_attachment: Optional[str]
    course_id: CourseSchemaOut
    created_at: datetime
    updated_at: datetime

class CourseCommentOut(Schema):
    id: int
    content_id: CourseContentMini
    member_id: CourseMemberOut
    comment: str
    created_at: datetime
    updated_at: datetime


class CourseCommentIn(Schema):
    comment: str

class RegisterIn(Schema):
    username: str
    password: str
    email: str
    first_name: str
    last_name: str


class RegisterOut(Schema): 
    id: int
    username: str
    email: str
    first_name: str
    last_name: str

class CourseSchemaIn(Schema):
    name: str
    description: str
    price: int


class CourseAddIn(Schema):
    name: str
    description: str
    price: int
    teacher_id: int


class EnrollStudentIn(Schema):
    user_id: List[int]
    role: str = "std"
    
class EnrollStudentOut(BaseModel):
    message: str



class ApproveCommentRequest(Schema):
    comment_ids: List[int]

class CourseContentIn(Schema):
    name: str
    description: str
    scheduled_start_time: Optional[datetime] = None
    scheduled_end_time: Optional[datetime] = None

class AnnouncementIn(Schema):
    title: str
    content: str
    start_date: datetime
    end_date: datetime
    course_id: Optional[int] = None

class AnnouncementOut(Schema):
    id: int
    title: str
    content: str
    start_date: datetime
    end_date: datetime
    created_at: datetime
    updated_at: datetime

class CategoryIn(Schema):
    name: str

class CategoryOut(Schema):
    id: int
    name: str
    created_by_id: Optional[int] = None
    created_at: datetime

class FeedbackIn(Schema):
    feedback: str

class FeedbackOut(Schema):
    id: int
    course_id: int
    user_id: int
    feedback: str
    created_at: str
    updated_at: str    

class CompletionIn(Schema):
    content_id: int

class CompletionOut(Schema):
    id: int
    content_id: int
    content_name: str
    course_id: int
    course_name: str
    completed_at: datetime
    user: UserOut  # Using your existing UserOut schema

    @staticmethod
    def from_orm(completion):
        return CompletionOut(
            id=completion.id,
            content_id=completion.content.id,
            content_name=completion.content.name,
            course_id=completion.content.course_id.id,
            course_name=completion.content.course_id.name,
            completed_at=completion.completed_at,
            user=UserOut.from_orm(completion.user)
        )

class CompletionStatsOut(Schema):
    total_contents: int
    completed: int
    progress: float

    @staticmethod
    def create(total: int, completed: int):
        return CompletionStatsOut(
            total_contents=total,
            completed=completed,
            progress=round((completed / total) * 100, 2) if total > 0 else 0
        )
    
class CourseOut(Schema):
    id: int
    name: str

class ContentOut(Schema):
    id: int
    name: str
    description: str
    course: CourseOut

class BookmarkOut(Schema):
    id: int
    bookmarked_at: datetime
    content: ContentOut

class ContentUpdateSchema(Schema):
    name: str | None = None
    description: str | None = None
    is_published: bool | None = None

class CourseOut(Schema):
    id: int
    name: str

class ContentOut(Schema):
    id: int
    name: str
    description: str
    is_published: bool
    course_id: CourseOut  # ✅ Ganti dari `course` ke `course_id`

class EnrollStudentIn(Schema):
    user_id: List[int]
    role: str = "std"

class EnrollStudentOut(Schema):
    message: str
class EnrollStudentIn(Schema):
    user_id: List[int]
    role: str = "std"

class EnrollStudentOut(Schema):
    message: str

class CourseAnalyticsOut(Schema):
    course_id: int
    course_name: str
    members_count: int
    contents_count: int
    comments_count: int
    feedback_count: int

class UserProfileOut(Schema):
    id: int
    first_name: str
    last_name: str
    email: str
    handphone: Optional[str]
    description: Optional[str]
    profile_picture: Optional[str]
    courses_created: list[CourseContentMini]
    courses_joined: list[CourseContentFull]

class CompletionTrackingCreateSchema(Schema):
    student_username: str  
    content_id: int
    course_id: int
    
    
class CompletionTrackingResponseSchema(Schema):
    content_name: str  
    completed_at: datetime  
    completed: bool

class CompletionTrackingResponseSchema(Schema):
    content_name: str  
    completed_at: datetime  
    completed: bool