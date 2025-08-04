from dataclasses import dataclass, asdict
from typing import List, Optional
from pydantic import BaseModel, Field
from enum import Enum

@dataclass
class OCRResult:
    """OCR kết quả với bounding box, text và confidence"""
    box: List[List[float]]
    text: str
    confidence: float
    
    def to_dict(self):
        return asdict(self)


@dataclass
class TOPIKQuestion:
    """Cấu trúc câu hỏi TOPIK theo schema CSV - Legacy compatibility"""
    question_id: str
    source: str
    question_number: int
    skill_area: str
    question_type: str
    passage: str
    passage_summary: str
    question_prompt: str
    option_1: str
    option_2: str
    option_3: str
    option_4: str
    correct_answer: Optional[int]
    explanation: str
    keywords: str
    difficulty: str
    audio_file: str
    image: str = ""
    
    def to_dict(self):
        return asdict(self)


# New Pydantic Models for enhanced processing
class SkillArea(str, Enum):
    """Enum cho các kỹ năng TOPIK"""
    READING = "읽기"
    LISTENING = "듣기" 
    WRITING = "쓰기"


class TOPIKQuestionPydantic(BaseModel):
    """Enhanced Pydantic model cho câu hỏi TOPIK với validation"""
    question_id: str = Field(..., description="Unique ID T{Level}{Skill}_{Test}_{Number}")
    source: str = Field(..., description="Source of the question")
    question_number: int = Field(..., description="Question number", ge=1)
    skill_area: SkillArea = Field(..., description="Skill area")
    question_type: str = Field(..., description="Question type")
    passage: str = Field("", description="Passage/content")
    passage_summary: str = Field("", description="Passage summary")
    question_prompt: str = Field(..., description="Main question")
    option_1: str = Field("", description="Option 1")
    option_2: str = Field("", description="Option 2")
    option_3: str = Field("", description="Option 3")
    option_4: str = Field("", description="Option 4")
    correct_answer: Optional[int] = Field(None, description="Correct answer 1-4", ge=1, le=4)
    explanation: str = Field("", description="Explanation")
    keywords: str = Field("", description="Keywords")
    difficulty: str = Field("", description="Difficulty")
    audio_file: str = Field("", description="Audio file")
    image: str = Field("", description="Image file")

    def to_legacy_dict(self) -> dict:
        """Convert to legacy TOPIKQuestion dict format"""
        return {
            "question_id": self.question_id,
            "source": self.source,
            "question_number": self.question_number,
            "skill_area": self.skill_area.value,
            "question_type": self.question_type,
            "passage": self.passage,
            "passage_summary": self.passage_summary,
            "question_prompt": self.question_prompt,
            "option_1": self.option_1,
            "option_2": self.option_2,
            "option_3": self.option_3,
            "option_4": self.option_4,
            "correct_answer": self.correct_answer,
            "explanation": self.explanation,
            "keywords": self.keywords,
            "difficulty": self.difficulty,
            "audio_file": self.audio_file,
            "image": self.image
        }


class TOPIKBatchResult(BaseModel):
    """Kết quả xử lý batch nhiều ảnh với PydanticAI"""
    questions: List[TOPIKQuestionPydantic] = Field(..., description="list of TOPIK questions")
    total_questions: int = Field(..., description="total number of questions")
    source_images: List[str] = Field(..., description="list of source images")
    processing_notes: str = Field("", description="processing notes in English")