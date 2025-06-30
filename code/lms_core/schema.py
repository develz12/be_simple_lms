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