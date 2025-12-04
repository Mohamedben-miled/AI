"""
Adaptive Tutoring Service
Manages section-by-section learning with quizzes and adaptive feedback
Enhanced with progressive explanations and 100% understanding requirement
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
    QUIZ_RETEACH = "quiz_reteach"  # For re-teaching after wrong reasoning
    QUIZ_COMPLETE = "quiz_complete"  # After passing a quiz, ask if more questions needed
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
            'explanation_attempts': 0,  # Track how many times we've explained (max 5)
            'quiz_count': 0,  # Track how many quizzes completed in current section
            'section_understanding': {},  # Track understanding per section (0.0 to 1.0)
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
        elif state == TutoringState.QUIZ_RETEACH:
            return self._handle_quiz_reteach(session_id, user_message)
        elif state == TutoringState.QUIZ_COMPLETE:
            return self._handle_quiz_complete(session_id, user_message)
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
- Explains that you'll only move forward when they fully understand (100%)
- Encourages them with enthusiasm

Be friendly and conversational."""
        
        intro = self.gpt_service.chat(prompt)
        if not intro:
            intro = f"Welcome! I'm excited to help you dive into this document. We'll go through it section by section, and you can ask me questions whenever you like. After each section, we'll have a quick quiz to make sure everything's clear. Don't worry—I'll only move on when you've truly understood each part. Let's get started—you're going to do great!"
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
        
        # Reset explanation attempts and quiz count for new section
        session['explanation_attempts'] = 0
        session['quiz_count'] = 0
        
        # If section text is too short (just title/header), get more content
        # Check if section_text is meaningful or just title/header
        cleaned_text = section_text.strip()
        
        # If section text is too short (less than 100 chars), try to get more content
        if len(cleaned_text) < 100:
            print(f"[TUTORING] Section text too short ({len(cleaned_text)} chars), attempting to get more content...")
            # Try to get content from full document text
            full_text = session.get('text', '')
            if full_text:
                # Find where this section starts in the full text
                title_pos = full_text.find(section_title)
                if title_pos != -1:
                    # Get content starting from title (next 1000-2000 chars)
                    section_start = title_pos
                    section_end = min(section_start + 2000, len(full_text))
                    cleaned_text = full_text[section_start:section_end].strip()
                    # Clean up - remove title if it's at the start
                    if cleaned_text.startswith(section_title):
                        cleaned_text = cleaned_text[len(section_title):].strip()
                else:
                    # Fallback: use first part of full text for first section
                    if section_index == 0:
                        cleaned_text = full_text[:1500].strip()
                    else:
                        # For other sections, combine with next section or use chunks
                        if section_index + 1 < len(sections):
                            next_section = sections[section_index + 1]
                            cleaned_text = section_text + "\n\n" + next_section.get('text', '')[:1000]
                        else:
                            cleaned_text = section_text
        
        # Remove excessive whitespace but keep paragraph breaks
        cleaned_text = '\n\n'.join([p.strip() for p in cleaned_text.split('\n\n') if p.strip()])
        
        # Remove very short lines that are likely headers/metadata
        lines = cleaned_text.split('\n')
        meaningful_lines = []
        for line in lines:
            line_stripped = line.strip()
            # Skip very short lines (likely headers/email/metadata) unless they're part of content
            if len(line_stripped) > 2 or (line_stripped and '@' not in line_stripped and len(meaningful_lines) > 0):
                meaningful_lines.append(line)
        
        cleaned_text = '\n'.join(meaningful_lines).strip()
        
        # Ensure we have meaningful content to read
        if len(cleaned_text) < 50:
            # Last resort: use title and ask for clarification
            cleaned_text = f"The section '{section_title}' contains important information. Let me read what's available."
        
        # If text is still too long, read it in chunks (but read the actual text)
        if len(cleaned_text) > 2000:
            # Read first part now, can continue reading if user wants
            cleaned_text = cleaned_text[:2000] + '...'
        
        # Generate a concise summary/explanation instead of reading verbatim
        # Use GPT to create a clear, educational summary of the section
        summary_prompt = f"""You are a tutor explaining a section from a document to a student. Create a clear, concise summary/explanation.

Section Title: {section_title}

Section Content:
{cleaned_text[:1500]}{'...' if len(cleaned_text) > 1500 else ''}

Your task:
1. Start with "Let me explain section {section_index + 1}: {section_title}"
2. Create a concise summary (3-5 sentences) that explains the KEY CONCEPTS
3. Make it educational and easy to understand
4. Focus on the main ideas, not every detail
5. Use clear, simple language
6. End with: "That's the summary of section {section_index + 1}. Do you have any questions, or are you ready for a quiz?"

Example format:
"Let me explain section 1: Fine-Tuning Large Language Models. Fine-tuning is a process where we take a pre-trained AI model and adapt it for specific tasks. It's like giving specialized training to a smart student. This is useful when basic prompting or RAG isn't enough. There are different types like full fine-tuning and parameter-efficient methods like LoRA. That's the summary of section 1. Do you have any questions, or are you ready for a quiz?"

Now create the summary:"""
        
        narration = self.gpt_service.chat(summary_prompt)
        if not narration or len(narration.strip()) < 50:
            # Fallback: create a simple summary
            preview = cleaned_text[:300].strip()
            narration = f"Let me explain section {section_index + 1}: {section_title}\n\n{preview}{'...' if len(cleaned_text) > 300 else ''}\n\nThat's the summary of section {section_index + 1}. Do you have any questions, or are you ready for a quiz?"
        
        print(f"[TUTORING] Summarizing section {section_index + 1}: {len(cleaned_text)} characters of content -> {len(narration)} character summary")
        
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
        move_on_keywords = ['next', 'continue', 'done', 'finished', 'move on', 'ready', 'quiz']
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
        
        # Reset explanation attempts for new quiz
        session['explanation_attempts'] = 0
        
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
            for line in lines:
                if line.startswith('QUESTION:'):
                    question_text = line.replace('QUESTION:', '').strip()
                elif line.startswith('CORRECT:'):
                    correct_answer = line.replace('CORRECT:', '').strip().upper()
                elif line and len(line) > 3 and line[0].isupper() and line[1:3] == ') ':
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
        """Handle user's quiz answer selection - check correctness immediately"""
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
        correct_answer = session['current_quiz_correct_answer']
        
        # Check if answer is correct immediately
        if answer_letter == correct_answer:
            # Correct answer - ask for reasoning
            session['state'] = TutoringState.QUIZ_REASONING
            message = f"You selected {answer_letter}. That's great! Now, I'd like to understand your thinking. Can you explain why you chose {answer_letter}? What was your reasoning?"
            
            session['conversation_history'].append({
                'role': 'assistant',
                'content': message
            })
            
            return {
                'message': message,
                'state': 'quiz_reasoning',
                'user_answer': answer_letter,
                'is_correct': True,
                'section_index': session['current_section_index']
            }
        else:
            # Wrong answer - provide explanation and point to document
            return self._handle_wrong_answer(session_id, answer_letter)
    
    def _handle_wrong_answer(self, session_id: str, user_answer: str) -> Dict:
        """Handle wrong answer with progressive explanations"""
        session = self.sessions[session_id]
        correct_answer = session['current_quiz_correct_answer']
        section_index = session['current_section_index']
        current_section = session['sections'][section_index]
        section_text = current_section.get('text', '')
        section_title = current_section.get('title', f'Section {section_index + 1}')
        question = session['current_quiz_question']
        options = session['current_quiz_options']
        
        # Increment explanation attempts
        session['explanation_attempts'] += 1
        attempts = session['explanation_attempts']
        
        # Get the correct option text
        correct_index = ord(correct_answer) - 65
        correct_option_text = options[correct_index] if correct_index < len(options) else ""
        
        # Determine explanation complexity (1 = normal, 5 = very simple)
        if attempts >= 5:
            complexity = 5  # Maximum simplification
        else:
            complexity = attempts
        
        # Generate explanation with progressive simplification
        prompt = f"""You are a patient tutor helping a student understand why their answer was incorrect. The student is learning and needs guidance.

Question: {question}

Options:
A) {options[0]}
B) {options[1]}
C) {options[2]}
D) {options[3]}

Correct Answer: {correct_answer}) {correct_option_text}
Student's Answer: {user_answer}

Section Title: {section_title}

Relevant Section Content (this is where the answer can be found):
{section_text[:2000]}{'...' if len(section_text) > 2000 else ''}

Your task:
1. Explain why the correct answer is {correct_answer}) {correct_option_text}
2. Point the student to WHERE in the section content they can find this information (mention specific parts)
3. Explain it in a way that matches complexity level {complexity} (1=normal, 5=very simple, use everyday language)
4. Be encouraging and supportive - they're learning!
5. After explaining, ask the same question again to test their understanding

Complexity guidelines:
- Level 1: Normal explanation
- Level 2-3: Use simpler words, break down concepts
- Level 4-5: Use very simple language, analogies, step-by-step breakdown

Format your response:
1. Acknowledge their answer briefly
2. Explain where in the section the answer is (quote or reference specific parts)
3. Explain why {correct_answer} is correct with appropriate complexity
4. End with: "Let me ask you the same question again: [question]" (copy the exact question)

Be warm and encouraging. The goal is learning, not judgment."""
        
        explanation = self.gpt_service.chat(prompt)
        if not explanation:
            explanation = f"Not quite. The correct answer is {correct_answer}) {correct_option_text}. Looking back at {section_title}, you can see that {correct_option_text}. Let me ask you the same question again: {question}"
        
        session['conversation_history'].append({
            'role': 'assistant',
            'content': explanation
        })
        
        # Stay in QUIZ_QUESTION state to ask again
        session['state'] = TutoringState.QUIZ_QUESTION
        
        return {
            'message': explanation,
            'state': 'quiz_question',
            'quiz_question': question,
            'quiz_options': options,
            'user_answer': user_answer,
            'is_correct': False,
            'explanation_attempts': attempts,
            'section_index': section_index,
            'section_title': section_title,
            'section_text': section_text,
            'highlight_section': True  # Flag to highlight section in frontend
        }
    
    def _handle_quiz_reasoning(self, session_id: str, user_message: str) -> Dict:
        """Evaluate user's reasoning - check if they truly understand"""
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
        
        # Evaluate reasoning using GPT
        prompt = f"""You are a tutor evaluating a student's reasoning for a quiz question. The student answered correctly, but you need to check if their REASONING shows true understanding.

Question: {question}

Options:
A) {options[0]}
B) {options[1]}
C) {options[2]}
D) {options[3]}

Correct Answer: {correct_answer}) {correct_option_text}
Student's Answer: {user_answer} (CORRECT)
Student's Reasoning: {user_message}

Section Content (for context):
{section_text[:2000]}{'...' if len(section_text) > 2000 else ''}

Your task:
1. Evaluate if the student's reasoning demonstrates TRUE understanding of WHY {correct_answer} is correct
2. Look for:
   - Correct reasoning that shows they understand the concept
   - Wrong/confused reasoning (even though answer was correct by luck)
   - Missing understanding of key concepts
   - Vague or memorized responses without real comprehension

Decide:
- If reasoning shows TRUE understanding: Confirm and move on
- If reasoning is wrong/confused/incomplete: Re-teach the concept more deeply

Respond with EXACTLY one of these two formats:

If reasoning is CORRECT:
REASONING_EVALUATION: CORRECT
FEEDBACK: [Brief encouraging message confirming their understanding, 1-2 sentences]

If reasoning is WRONG or needs improvement:
REASONING_EVALUATION: INCORRECT
FEEDBACK: [Explain the concept more deeply, point to the section content, help them understand WHY {correct_answer} is correct. Use clear, simple explanations. 3-4 sentences. Be encouraging.]"""
        
        evaluation_response = self.gpt_service.chat(prompt)
        
        # Parse evaluation
        reasoning_correct = False
        feedback = ""
        
        if evaluation_response:
            lines = evaluation_response.strip().split('\n')
            for i, line in enumerate(lines):
                if 'REASONING_EVALUATION:' in line:
                    if 'CORRECT' in line.upper():
                        reasoning_correct = True
                    elif 'INCORRECT' in line.upper():
                        reasoning_correct = False
                elif 'FEEDBACK:' in line:
                    # Get feedback (could be on same line or next lines)
                    feedback = line.replace('FEEDBACK:', '').strip()
                    if i + 1 < len(lines):
                        # Check if feedback continues on next lines
                        next_lines = '\n'.join(lines[i+1:])
                        if next_lines.strip():
                            feedback += " " + next_lines.strip()
        
        if not feedback:
            # Fallback
            reasoning_correct = True  # Default to correct if parsing fails
            feedback = "Great! Your reasoning shows you understand the concept. Well done!"
        
        session['conversation_history'].append({
            'role': 'assistant',
            'content': feedback
        })
        
        if reasoning_correct:
            # Reasoning is correct - increment quiz count and ask if they want more questions
            session['quiz_count'] = session.get('quiz_count', 0) + 1
            session['section_understanding'][section_index] = min(1.0, session['quiz_count'] * 0.33)  # 3 quizzes = 100%
            
            print(f"[TUTORING] Quiz {session['quiz_count']} passed for section {section_index + 1}")
            
            # Ask if they want more questions or move to next section
            session['state'] = TutoringState.QUIZ_COMPLETE
            
            quiz_count = session['quiz_count']
            message = f"{feedback}\n\nGreat job! You've completed {quiz_count} quiz question(s) for this section. Would you like me to ask you another question to make sure you really understand, or are you ready to move on to the next section? (Say 'more questions', 'another question', 'next section', or 'continue')"
            
            session['conversation_history'].append({
                'role': 'assistant',
                'content': message
            })
            
            return {
                'message': message,
                'state': 'quiz_complete',
                'section_index': section_index,
                'section_title': section_title,
                'section_text': section_text,
                'quiz_count': quiz_count,
                'can_skip_to_next': True  # Flag for frontend to show "Next Section" button
            }
        else:
            # Reasoning is wrong - re-teach the concept
            session['state'] = TutoringState.QUIZ_RETEACH
            return {
                'message': feedback,
                'state': 'quiz_reteach',
                'section_index': section_index,
                'section_title': section_title,
                'section_text': section_text,
                'highlight_section': True,
                'quiz_question': question,
                'quiz_options': options
            }
    
    def _handle_quiz_complete(self, session_id: str, user_message: str) -> Dict:
        """Handle user response after completing a quiz - offer more questions or move to next section"""
        session = self.sessions[session_id]
        user_lower = user_message.lower().strip()
        
        # Check if user wants to move to next section
        next_keywords = ['next section', 'move on', 'continue', 'next', 'skip', 'done with this section']
        if any(keyword in user_lower for keyword in next_keywords):
            # User wants to move to next section
            section_index = session['current_section_index']
            session['section_understanding'][section_index] = 1.0  # Mark as complete
            return self._complete_section(session_id, "Great! Let's move on to the next section.")
        
        # Check if user wants more questions
        more_keywords = ['more questions', 'another question', 'ask me more', 'more', 'yes', 'sure', 'okay', 'ok']
        if any(keyword in user_lower for keyword in more_keywords):
            # Generate another quiz question for this section
            return self._generate_quiz_questions(session_id)
        
        # Default: ask for clarification
        message = "I didn't quite understand. Would you like me to ask you another question about this section, or are you ready to move on to the next section? (Say 'more questions' or 'next section')"
        
        session['conversation_history'].append({
            'role': 'assistant',
            'content': message
        })
        
        return {
            'message': message,
            'state': 'quiz_complete',
            'section_index': session['current_section_index'],
            'section_title': session['sections'][session['current_section_index']].get('title', 'Current Section'),
            'can_skip_to_next': True
        }
    
    def _handle_quiz_reteach(self, session_id: str, user_message: str) -> Dict:
        """Handle re-teaching after wrong reasoning - ask the question again"""
        session = self.sessions[session_id]
        
        # Check if user understands now
        user_lower = user_message.lower().strip()
        understanding_keywords = ['yes', 'yeah', 'understand', 'got it', 'clear', 'okay', 'ok', 'ready']
        
        if any(keyword in user_lower for keyword in understanding_keywords):
            # User says they understand - ask the question again to verify
            question = session['current_quiz_question']
            options = session['current_quiz_options']
            
            session['state'] = TutoringState.QUIZ_QUESTION
            
            message = f"Great! Let's make sure you've got it. I'll ask you the same question again:\n\n{question}\n\n"
            for i, option in enumerate(options):
                letter = chr(65 + i)
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
        else:
            # User might have more questions or needs more explanation
            section_index = session['current_section_index']
            current_section = session['sections'][section_index]
            section_text = current_section.get('text', '')
            section_title = current_section.get('title', f'Section {section_index + 1}')
            
            prompt = f"""The student needs more help understanding. They said: "{user_message}"

Section Title: {section_title}
Section Content: {section_text[:2000]}

Provide a more detailed, simpler explanation. Help them understand the concept better. After explaining, ask if they're ready to try the question again."""
            
            further_explanation = self.gpt_service.chat(prompt)
            if not further_explanation:
                further_explanation = "Let me explain this more clearly. Would you like me to go through it again, or are you ready to try the question?"
            
            session['conversation_history'].append({
                'role': 'assistant',
                'content': further_explanation
            })
            
            return {
                'message': further_explanation,
                'state': 'quiz_reteach',
                'section_index': section_index,
                'section_title': section_title,
                'section_text': section_text
            }
    
    def _complete_section(self, session_id: str, feedback_message: str) -> Dict:
        """Complete current section and move to next - only called when understanding is 100%"""
        session = self.sessions[session_id]
        old_index = session['current_section_index']
        session['current_section_index'] += 1
        new_index = session['current_section_index']
        
        print(f"[TUTORING] Completing section {old_index + 1}, moving to section {new_index + 1}")
        
        # Reset explanation attempts for next section
        session['explanation_attempts'] = 0
        
        if session['current_section_index'] >= len(session['sections']):
            # All sections completed
            print(f"[TUTORING] All sections completed!")
            session['state'] = TutoringState.DOCUMENT_COMPLETE
            return self._generate_completion_message(session_id)
        else:
            # Move to next section
            session['state'] = TutoringState.SECTION_READING
            next_section_response = self._present_section(session_id)
            
            print(f"[TUTORING] Next section prepared: {next_section_response.get('section_title', 'N/A')}")
            
            # Combine feedback with next section message
            combined_message = f"{feedback_message}\n\n{next_section_response['message']}"
            
            return {
                'message': combined_message,
                'state': 'section_qna',
                'section_index': next_section_response['section_index'],
                'section_title': next_section_response['section_title'],
                'section_text': next_section_response.get('section_text', ''),
                'sections': session['sections']  # Include all sections for frontend
            }
    
    def _generate_completion_message(self, session_id: str) -> Dict:
        """Generate completion message when all sections are done"""
        session = self.sessions[session_id]
        section_count = len(session['sections'])
        
        prompt = f"""You are a tutor congratulating a student who just completed going through all {section_count} sections of a document with quizzes. 

Create an encouraging completion message (2-3 sentences) that:
- Congratulates them warmly
- Acknowledges their effort and learning
- Notes that they achieved 100% understanding in each section
- Encourages them to keep learning
- Is enthusiastic and positive

Be genuine and celebratory."""
        
        completion_msg = self.gpt_service.chat(prompt)
        if not completion_msg:
            completion_msg = f"Congratulations! You've completed all {section_count} sections with full understanding. You did an amazing job! Keep up the great work and continue learning!"
        
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
