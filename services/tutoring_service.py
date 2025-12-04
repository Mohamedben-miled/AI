"""
Adaptive Tutoring Service
Manages section-by-section learning with quizzes and adaptive feedback
"""
from enum import Enum
from typing import Dict, List, Optional, Tuple
from services.gpt import GPTService

class TutoringState(Enum):
    """State machine for tutoring flow"""
    INTRODUCTION = "introduction"
    SECTION_READING = "section_reading"
    SECTION_QNA = "section_qna"
    QUIZ_QUESTION = "quiz_question"
    QUIZ_REASONING = "quiz_reasoning"
    DOCUMENT_COMPLETE = "document_complete"

class TutoringService:
    def __init__(self, gpt_service: GPTService):
        self.gpt_service = gpt_service
        self.sessions: Dict[str, Dict] = {}
    
    def start_tutoring_session(self, document_id: str, text: str, sections: List[Dict], session_id: str = None) -> str:
        """
        Start a new tutoring session
        
        Args:
            document_id: ID of the document being tutored
            text: Full text of the document
            sections: List of section dictionaries with 'title' and 'text'
            session_id: Optional session ID (generated if not provided)
            
        Returns:
            str: Session ID
        """
        import uuid
        if not session_id:
            session_id = f"tutoring_{uuid.uuid4().hex[:8]}"
        
        # Initialize session state
        self.sessions[session_id] = {
            'document_id': document_id,
            'text': text,
            'sections': sections,
            'current_section_index': 0,
            'state': TutoringState.INTRODUCTION,
            'current_quiz_question': None,
            'current_quiz_options': None,
            'current_quiz_correct_answer': None,
            'section_understanding': {},  # Track understanding per section
            'conversation_history': []
        }
        
        # Generate introduction
        introduction = self._generate_introduction(sections)
        self.sessions[session_id]['conversation_history'].append({
            'role': 'assistant',
            'content': introduction
        })
        
        return session_id
    
    def process_user_message(self, session_id: str, user_message: str) -> Dict:
        """
        Process user message and return AI response based on current state
        
        Args:
            session_id: Tutoring session ID
            user_message: User's message/input
            
        Returns:
            Dict: Response with message, state, and metadata
        """
        if session_id not in self.sessions:
            return {
                'error': 'Session not found',
                'message': 'Please start a new tutoring session.'
            }
        
        session = self.sessions[session_id]
        state = session['state']
        
        # Add user message to history
        session['conversation_history'].append({
            'role': 'user',
            'content': user_message
        })
        
        # Route based on state
        if state == TutoringState.INTRODUCTION:
            return self._handle_introduction(session_id, user_message)
        elif state == TutoringState.SECTION_READING:
            return self._handle_section_reading(session_id, user_message)
        elif state == TutoringState.SECTION_QNA:
            return self._handle_section_qna(session_id, user_message)
        elif state == TutoringState.QUIZ_QUESTION:
            return self._handle_quiz_answer(session_id, user_message)
        elif state == TutoringState.QUIZ_REASONING:
            return self._handle_quiz_reasoning(session_id, user_message)
        else:
            return {
                'message': 'The tutoring session has been completed. Great job!',
                'state': 'complete'
            }
    
    def _generate_introduction(self, sections: List[Dict]) -> str:
        """Generate welcoming introduction message"""
        section_count = len(sections)
        prompt = f"""You are an excellent, patient, and adaptive tutor. A student is about to start learning from a document that has {section_count} sections. 

Create a warm, encouraging introduction message (2-3 sentences) that:
- Welcomes them warmly
- Explains that you'll go through the document section by section
- Mentions they can ask questions anytime
- Explains there will be quizzes after each section to check understanding
- Encourages them with enthusiasm

Be friendly and conversational."""
        
        intro = self.gpt_service.chat(prompt)
        if not intro:
            intro = f"Welcome! I'm excited to help you dive into this document. We'll go through it section by section, and you can ask me questions whenever you like. After each section, we'll have a quick quiz to make sure everything's clear. Let's get started—you're going to do great!"
        return intro
    
    def _handle_introduction(self, session_id: str, user_message: str) -> Dict:
        """Handle introduction state - automatically move to first section"""
        session = self.sessions[session_id]
        session['state'] = TutoringState.SECTION_READING
        
        return self._present_section(session_id)
    
    def _present_section(self, session_id: str) -> Dict:
        """Present the current section to the user"""
        session = self.sessions[session_id]
        section_index = session['current_section_index']
        sections = session['sections']
        
        if section_index >= len(sections):
            # All sections completed
            return self._generate_completion_message(session_id)
        
        current_section = sections[section_index]
        section_title = current_section.get('title', f'Section {section_index + 1}')
        section_text = current_section.get('text', '')
        
        # Generate narration of the section
        prompt = f"""You are a great tutor narrating a section of a document to a student. The section is:

Title: {section_title}

Content:
{section_text[:2000]}{'...' if len(section_text) > 2000 else ''}

Narrate this section in a clear, engaging way (2-4 sentences). Explain the key concepts naturally as if you're teaching in person. Make it conversational and easy to follow. Don't just repeat the text—explain it as a good teacher would."""
        
        narration = self.gpt_service.chat(prompt)
        if not narration:
            narration = f"Let's look at {section_title}. {section_text[:500]}..."
        
        session['state'] = TutoringState.SECTION_QNA
        session['conversation_history'].append({
            'role': 'assistant',
            'content': narration
        })
        
        return {
            'message': narration,
            'state': 'section_qna',
            'section_index': section_index,
            'section_title': section_title,
            'section_text': section_text
        }
    
    def _handle_section_reading(self, session_id: str, user_message: str) -> Dict:
        """Handle user response during section reading - move to Q&A"""
        return self._present_section(session_id)
    
    def _handle_section_qna(self, session_id: str, user_message: str) -> Dict:
        """Handle user questions during section Q&A phase"""
        session = self.sessions[session_id]
        section_index = session['current_section_index']
        sections = session['sections']
        current_section = sections[section_index]
        section_text = current_section.get('text', '')
        section_title = current_section.get('title', f'Section {section_index + 1}')
        
        # Check if user wants to move on
        user_lower = user_message.lower().strip()
        move_on_keywords = ['next', 'continue', 'done', 'finished', 'move on', 'ready']
        if any(keyword in user_lower for keyword in move_on_keywords):
            # Generate quiz for this section
            return self._generate_quiz_questions(session_id)
        
        # Answer question based ONLY on current section (no new information)
        prompt = f"""You are a tutor helping a student understand a specific section of a document. 

IMPORTANT RULES:
1. ONLY answer based on the current section content provided below
2. DO NOT introduce any new information not in this section
3. If the question is about something not covered in this section, politely say "That's a great question! However, we haven't covered that yet in this section. Let's focus on understanding {section_title} first. What would you like to know about this section?"
4. If the question is about the current section, answer clearly and helpfully
5. Keep responses concise (2-3 sentences)

Current Section:
Title: {section_title}

Content:
{section_text[:2000]}{'...' if len(section_text) > 2000 else ''}

Student's question: {user_message}

Provide your response:"""
        
        answer = self.gpt_service.chat(prompt)
        if not answer:
            answer = "I'd be happy to help! Could you rephrase your question about this section?"
        
        session['conversation_history'].append({
            'role': 'assistant',
            'content': answer
        })
        
        return {
            'message': answer,
            'state': 'section_qna',
            'section_index': section_index,
            'section_title': section_title
        }
    
    def _generate_quiz_questions(self, session_id: str) -> Dict:
        """Generate quiz questions for the current section"""
        session = self.sessions[session_id]
        section_index = session['current_section_index']
        sections = session['sections']
        current_section = sections[section_index]
        section_text = current_section.get('text', '')
        section_title = current_section.get('title', f'Section {section_index + 1}')
        
        prompt = f"""You are a tutor creating a knowledge-based quiz question to test understanding of a section. 

Section Title: {section_title}

Section Content:
{section_text[:2000]}{'...' if len(section_text) > 2000 else ''}

Create ONE multiple-choice question (with 4 options) that tests if the student actually understood the key concepts from this section. The question should be:
- Clear and specific
- Test actual understanding, not just memorization
- Have one clearly correct answer
- Have 3 plausible but incorrect distractors

Format your response EXACTLY like this:
QUESTION: [the question text]
A) [option A]
B) [option B]
C) [option C]
D) [option D]
CORRECT: [the letter of the correct answer, e.g., B]

Make sure the question tests understanding, not just recall."""
        
        quiz_response = self.gpt_service.chat(prompt)
        
        # Parse quiz response
        question_text = None
        options = []
        correct_answer = None
        
        if quiz_response:
            lines = quiz_response.strip().split('\n')
            current_section_name = None
            for line in lines:
                if line.startswith('QUESTION:'):
                    question_text = line.replace('QUESTION:', '').strip()
                elif line.startswith('CORRECT:'):
                    correct_answer = line.replace('CORRECT:', '').strip().upper()
                elif line and (line[0].isupper() and line[1:3] == ') '):
                    options.append(line[3:].strip())
        
        # Fallback if parsing failed
        if not question_text or not options or not correct_answer:
            question_text = f"What is a key concept from {section_title}?"
            options = ["Option A", "Option B", "Option C", "Option D"]
            correct_answer = "A"
        
        session['current_quiz_question'] = question_text
        session['current_quiz_options'] = options
        session['current_quiz_correct_answer'] = correct_answer
        session['state'] = TutoringState.QUIZ_QUESTION
        
        return self._present_quiz_question(session_id)
    
    def _present_quiz_question(self, session_id: str) -> Dict:
        """Present the quiz question to the user"""
        session = self.sessions[session_id]
        question = session['current_quiz_question']
        options = session['current_quiz_options']
        
        message = f"Great! Now let's see how well you understood this section. Here's a question for you:\n\n{question}\n\n"
        for i, option in enumerate(options):
            letter = chr(65 + i)  # A, B, C, D
            message += f"{letter}) {option}\n"
        
        message += "\nPlease select your answer (A, B, C, or D)."
        
        session['conversation_history'].append({
            'role': 'assistant',
            'content': message
        })
        
        return {
            'message': message,
            'state': 'quiz_question',
            'quiz_question': question,
            'quiz_options': options,
            'section_index': session['current_section_index'],
            'section_title': session['sections'][session['current_section_index']].get('title', 'Current Section')
        }
    
    def _handle_quiz_answer(self, session_id: str, user_message: str) -> Dict:
        """Handle user's quiz answer selection"""
        session = self.sessions[session_id]
        user_answer = user_message.strip().upper()
        
        # Extract letter from answer (A, B, C, or D)
        answer_letter = None
        if len(user_answer) > 0 and user_answer[0] in ['A', 'B', 'C', 'D']:
            answer_letter = user_answer[0]
        
        if not answer_letter:
            # Invalid answer format
            return {
                'message': "Please provide your answer as a single letter: A, B, C, or D.",
                'state': 'quiz_question',
                'quiz_question': session['current_quiz_question'],
                'quiz_options': session['current_quiz_options']
            }
        
        # Store the user's answer
        session['user_quiz_answer'] = answer_letter
        session['state'] = TutoringState.QUIZ_REASONING
        
        # Ask for reasoning
        message = f"You selected {answer_letter}. That's great! Now, I'd like to understand your thinking. Can you explain why you chose {answer_letter}? What was your reasoning?"
        
        session['conversation_history'].append({
            'role': 'assistant',
            'content': message
        })
        
        return {
            'message': message,
            'state': 'quiz_reasoning',
            'user_answer': answer_letter,
            'section_index': session['current_section_index']
        }
    
    def _handle_quiz_reasoning(self, session_id: str, user_message: str) -> Dict:
        """Evaluate user's reasoning and provide adaptive feedback"""
        session = self.sessions[session_id]
        user_answer = session['user_quiz_answer']
        correct_answer = session['current_quiz_correct_answer']
        section_index = session['current_section_index']
        current_section = session['sections'][section_index]
        section_text = current_section.get('text', '')
        question = session['current_quiz_question']
        options = session['current_quiz_options']
        
        # Get the correct option text
        correct_index = ord(correct_answer) - 65
        correct_option_text = options[correct_index] if correct_index < len(options) else ""
        
        # Evaluate reasoning
        prompt = f"""You are a tutor evaluating a student's quiz answer and reasoning.

Question: {question}

Options:
A) {options[0]}
B) {options[1]}
C) {options[2]}
D) {options[3]}

Correct Answer: {correct_answer}) {correct_option_text}

Student's Answer: {user_answer}
Student's Reasoning: {user_message}

Section Content (for context):
{section_text[:1500]}

Your task:
1. Determine if the student's answer is correct
2. Evaluate if their reasoning demonstrates actual understanding
3. The goal is LEARNING, not just correctness

Scenarios:
- If answer is correct AND reasoning shows understanding: Confirm and encourage, then move on
- If answer is correct BUT reasoning is wrong/confused: Help them understand WHY it's correct with a clear explanation, then ask if they understand
- If answer is wrong: Don't just say it's wrong. Explain the correct answer in a way that helps them learn, using simpler language if needed. Check if they understand.

Generate your feedback (2-4 sentences). Be encouraging and focused on learning. If they don't understand, explain it more simply."""
        
        feedback = self.gpt_service.chat(prompt)
        if not feedback:
            if user_answer == correct_answer:
                feedback = "Great! Your answer is correct. Let's move on to the next section!"
            else:
                feedback = f"The correct answer is {correct_answer}. Let me explain why..."
        
        session['conversation_history'].append({
            'role': 'assistant',
            'content': feedback
        })
        
        # Check if we should move on or continue explaining
        # For now, always move on after feedback (can be enhanced with follow-up questions)
        # Mark understanding for this section
        understanding_score = 1.0 if user_answer == correct_answer else 0.5
        session['section_understanding'][section_index] = understanding_score
        
        # Move to next section or complete
        return self._complete_section(session_id, feedback)
    
    def _complete_section(self, session_id: str, feedback_message: str) -> Dict:
        """Complete current section and move to next"""
        session = self.sessions[session_id]
        session['current_section_index'] += 1
        
        if session['current_section_index'] >= len(session['sections']):
            # All sections completed
            session['state'] = TutoringState.DOCUMENT_COMPLETE
            return self._generate_completion_message(session_id)
        else:
            # Move to next section
            session['state'] = TutoringState.SECTION_READING
            next_section_response = self._present_section(session_id)
            
            # Combine feedback with next section
            return {
                'message': feedback_message + "\n\n" + next_section_response['message'],
                'state': 'section_qna',
                'section_index': next_section_response['section_index'],
                'section_title': next_section_response['section_title'],
                'section_text': next_section_response.get('section_text', '')
            }
    
    def _generate_completion_message(self, session_id: str) -> Dict:
        """Generate completion message when all sections are done"""
        session = self.sessions[session_id]
        section_count = len(session['sections'])
        
        prompt = f"""You are a tutor congratulating a student who just completed going through all {section_count} sections of a document with quizzes. 

Create an encouraging completion message (2-3 sentences) that:
- Congratulates them warmly
- Acknowledges their effort and learning
- Encourages them to keep learning
- Is enthusiastic and positive

Be genuine and celebratory."""
        
        completion_msg = self.gpt_service.chat(prompt)
        if not completion_msg:
            completion_msg = f"Congratulations! You've completed all {section_count} sections. You did an amazing job! Keep up the great work and continue learning!"
        
        session['state'] = TutoringState.DOCUMENT_COMPLETE
        session['conversation_history'].append({
            'role': 'assistant',
            'content': completion_msg
        })
        
        return {
            'message': completion_msg,
            'state': 'complete',
            'section_index': len(session['sections']) - 1
        }
    
    def get_session_state(self, session_id: str) -> Optional[Dict]:
        """Get current session state"""
        return self.sessions.get(session_id)

