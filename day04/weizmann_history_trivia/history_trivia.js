const QUESTIONS_PER_ROUND = 5;
const CHOICES = ["A", "B", "C", "D"];
const DIFFICULTIES = ["Easy", "Medium", "Hard"];
const POINTS_PER_ANSWER = 20;
const STREAK_BONUS = 5;
const MAX_ROUND_POINTS = QUESTIONS_PER_ROUND * POINTS_PER_ANSWER
  + (QUESTIONS_PER_ROUND - 1) * STREAK_BONUS;
const PERSONAL_BEST_KEY = "weizmannHistoryQuiz.personalBest";

const elements = {
  loading: document.querySelector("#loading-state"),
  error: document.querySelector("#error-state"),
  poolCount: document.querySelector("#pool-count"),
  selectionError: document.querySelector("#selection-error"),
  welcome: document.querySelector("#welcome-screen"),
  question: document.querySelector("#question-screen"),
  results: document.querySelector("#results-screen"),
  score: document.querySelector("#score-value"),
  bestScore: document.querySelector("#best-score"),
  roundCount: document.querySelector("#round-count"),
  streakStat: document.querySelector("#streak-stat"),
  streakCount: document.querySelector("#streak-count"),
  progressTrack: document.querySelector("#progress-track"),
  progress: document.querySelector("#progress-fill"),
  status: document.querySelector("#status-copy"),
  announcer: document.querySelector("#game-announcer"),
  questionNumber: document.querySelector("#question-number"),
  category: document.querySelector("#category-label"),
  difficultyLabel: document.querySelector("#difficulty-label"),
  questionText: document.querySelector("#question-text"),
  answers: document.querySelector("#answer-list"),
  feedbackRow: document.querySelector("#feedback-row"),
  feedbackCopy: document.querySelector(".feedback-copy"),
  feedbackTitle: document.querySelector("#feedback-title"),
  explanation: document.querySelector("#explanation-text"),
  next: document.querySelector("#next-button"),
  finalScore: document.querySelector("#final-score"),
  resultTitle: document.querySelector("#result-title"),
  resultCopy: document.querySelector("#result-copy"),
  resultSummary: document.querySelector("#result-summary"),
  missedReview: document.querySelector("#missed-review"),
  missedReviewList: document.querySelector("#missed-review-list"),
};

let questions = [];
let roundQuestions = [];
let questionIndex = 0;
let correctAnswers = 0;
let scorePoints = 0;
let currentStreak = 0;
let personalBest = 0;
let personalBestAvailable = true;
let locked = false;
let answerResults = [];

function parseCsv(text) {
  const rows = [];
  let row = [];
  let field = "";
  let quoted = false;

  for (let index = 0; index < text.length; index += 1) {
    const character = text[index];
    if (quoted) {
      if (character === '"' && text[index + 1] === '"') {
        field += '"';
        index += 1;
      } else if (character === '"') {
        quoted = false;
      } else {
        field += character;
      }
    } else if (character === '"') {
      quoted = true;
    } else if (character === ",") {
      row.push(field);
      field = "";
    } else if (character === "\n") {
      row.push(field.replace(/\r$/, ""));
      if (row.some((value) => value.trim())) rows.push(row);
      row = [];
      field = "";
    } else {
      field += character;
    }
  }

  if (field || row.length) {
    row.push(field.replace(/\r$/, ""));
    if (row.some((value) => value.trim())) rows.push(row);
  }
  if (quoted) throw new Error("The question file contains an unfinished quoted field.");

  const [headers, ...records] = rows;
  if (!headers) throw new Error("The question file is empty.");
  return records.map((values) => Object.fromEntries(
    headers.map((header, index) => [header.trim(), (values[index] || "").trim()]),
  ));
}

function shuffle(items) {
  const shuffled = [...items];
  for (let index = shuffled.length - 1; index > 0; index -= 1) {
    const swapIndex = Math.floor(Math.random() * (index + 1));
    [shuffled[index], shuffled[swapIndex]] = [shuffled[swapIndex], shuffled[index]];
  }
  return shuffled;
}

function showScreen(screen) {
  [elements.welcome, elements.question, elements.results].forEach((item) => {
    item.hidden = item !== screen;
  });
}

function updateScoreboard() {
  const answeredQuestions = Math.min(questionIndex + (locked ? 1 : 0), QUESTIONS_PER_ROUND);
  elements.score.textContent = String(scorePoints).padStart(2, "0");
  elements.roundCount.textContent = `${String(answeredQuestions).padStart(2, "0")} / ${String(QUESTIONS_PER_ROUND).padStart(2, "0")}`;
  elements.progress.style.width = `${(answeredQuestions / QUESTIONS_PER_ROUND) * 100}%`;
  elements.progressTrack.setAttribute("aria-valuenow", String(answeredQuestions));
  elements.progressTrack.setAttribute("aria-valuetext", `${answeredQuestions} of ${QUESTIONS_PER_ROUND} questions answered`);
  elements.streakStat.hidden = currentStreak === 0;
  elements.streakCount.textContent = `${currentStreak}×`;
}

function getSelectedDifficulty() {
  const selectedDifficulty = document.querySelector('input[name="difficulty"]:checked');
  if (!selectedDifficulty) throw new Error("Choose a difficulty before starting a round.");
  return selectedDifficulty.value;
}

function getEligibleQuestions() {
  return questions.filter((question) => question.difficulty === getSelectedDifficulty());
}

function updateQuestionPoolCount() {
  elements.poolCount.textContent = `${getEligibleQuestions().length} ${getSelectedDifficulty().toUpperCase()} QUESTIONS AVAILABLE · +20 CORRECT / +5 STREAK`;
}

function updatePersonalBestDisplay() {
  elements.bestScore.textContent = personalBestAvailable ? `${personalBest} PTS` : "N/A";
}

function loadPersonalBest() {
  try {
    const savedScore = window.localStorage.getItem(PERSONAL_BEST_KEY);
    if (savedScore !== null) {
      const parsedScore = Number(savedScore);
      if (!Number.isInteger(parsedScore) || parsedScore < 0 || parsedScore > MAX_ROUND_POINTS) {
        throw new Error("Saved personal best is not a valid score.");
      }
      personalBest = parsedScore;
    }
  } catch (error) {
    personalBestAvailable = false;
    console.error("Could not load the personal best from local storage.", error);
  }
  updatePersonalBestDisplay();
}

function savePersonalBestIfBeaten() {
  if (!personalBestAvailable || scorePoints <= personalBest) return false;
  try {
    window.localStorage.setItem(PERSONAL_BEST_KEY, String(scorePoints));
    personalBest = scorePoints;
    updatePersonalBestDisplay();
    return true;
  } catch (error) {
    personalBestAvailable = false;
    updatePersonalBestDisplay();
    console.error("Could not save the personal best to local storage.", error);
    return false;
  }
}

function startGame() {
  const selectedDifficulty = getSelectedDifficulty();
  const eligibleQuestions = getEligibleQuestions();
  if (eligibleQuestions.length < QUESTIONS_PER_ROUND) {
    elements.selectionError.textContent = `There are not enough ${selectedDifficulty.toLowerCase()} questions for a round.`;
    elements.selectionError.hidden = false;
    elements.selectionError.focus();
    return;
  }

  elements.selectionError.hidden = true;
  roundQuestions = shuffle(eligibleQuestions).slice(0, QUESTIONS_PER_ROUND);
  questionIndex = 0;
  correctAnswers = 0;
  scorePoints = 0;
  currentStreak = 0;
  locked = false;
  answerResults = [];
  elements.status.textContent = "ROUND IN PROGRESS";
  updateScoreboard();
  showScreen(elements.question);
  renderQuestion();
  elements.questionText.focus();
}

function renderQuestion() {
  const question = roundQuestions[questionIndex];
  locked = false;
  elements.questionNumber.textContent = `QUESTION ${String(questionIndex + 1).padStart(2, "0")} / ${String(QUESTIONS_PER_ROUND).padStart(2, "0")}`;
  elements.category.textContent = question.category.toUpperCase();
  elements.difficultyLabel.textContent = question.difficulty.toUpperCase();
  elements.questionText.textContent = question.question;
  elements.questionText.setAttribute("aria-label", `${question.category}. ${question.question}`);
  elements.feedbackRow.hidden = true;
  elements.feedbackCopy.className = "feedback-copy";
  elements.answers.replaceChildren();

  CHOICES.forEach((choice) => {
    const button = document.createElement("button");
    button.className = "answer-option";
    button.type = "button";
    button.dataset.choice = choice;
    const key = document.createElement("span");
    key.className = "answer-key";
    key.textContent = choice;
    const text = document.createElement("span");
    text.textContent = question[choice];
    button.append(key, text);
    button.addEventListener("click", () => submitAnswer(choice));
    elements.answers.append(button);
  });
}

function submitAnswer(choice) {
  if (locked) return;
  locked = true;
  const question = roundQuestions[questionIndex];
  const correctChoice = question.answer.trim().toUpperCase();
  const isCorrect = choice === correctChoice;
  let pointsAwarded = 0;
  if (isCorrect) {
    correctAnswers += 1;
    currentStreak += 1;
    pointsAwarded = POINTS_PER_ANSWER + (currentStreak > 1 ? STREAK_BONUS : 0);
    scorePoints += pointsAwarded;
  } else {
    currentStreak = 0;
  }
  answerResults.push({ question, choice, isCorrect });
  updateScoreboard();

  elements.answers.querySelectorAll(".answer-option").forEach((button) => {
    button.disabled = true;
    if (button.dataset.choice === correctChoice) {
      button.classList.add("correct");
    } else if (button.dataset.choice === choice) {
      button.classList.add("incorrect");
    } else {
      button.classList.add("muted");
    }
  });

  elements.feedbackCopy.classList.add(isCorrect ? "is-correct" : "is-wrong");
  elements.feedbackTitle.textContent = isCorrect
    ? `Correct: ${question[correctChoice]}. +${pointsAwarded} points${currentStreak > 1 ? `, including a +${STREAK_BONUS} streak bonus` : ""}.`
    : `Not quite. The correct answer is ${question[correctChoice]}.`;
  elements.explanation.textContent = question.explanation;
  elements.announcer.textContent = `${isCorrect ? "Correct." : "Not quite."} Score: ${scorePoints} points. ${questionIndex + 1} of ${QUESTIONS_PER_ROUND} questions answered.`;
  elements.next.innerHTML = questionIndex === QUESTIONS_PER_ROUND - 1
    ? 'SEE RESULTS <span aria-hidden="true">→</span>'
    : 'NEXT <span aria-hidden="true">→</span>';
  elements.feedbackRow.hidden = false;
  elements.next.focus();
}

function showResults() {
  questionIndex = QUESTIONS_PER_ROUND;
  updateScoreboard();
  const percentage = Math.round((correctAnswers / QUESTIONS_PER_ROUND) * 100);
  elements.finalScore.textContent = String(percentage).padStart(2, "0");
  elements.resultTitle.textContent = percentage === 100
    ? "Perfect score."
    : percentage >= 60 ? "Nice work." : "Keep exploring.";
  const newPersonalBest = savePersonalBestIfBeaten();
  const bestCopy = personalBestAvailable
    ? ` Personal best: ${personalBest} points.`
    : " Personal best storage is unavailable.";
  elements.resultCopy.textContent = `You got ${correctAnswers} out of ${QUESTIONS_PER_ROUND} questions right and scored ${scorePoints} points.${newPersonalBest ? " New personal best!" : bestCopy}`;
  elements.resultSummary.replaceChildren(...answerResults.map(({ isCorrect }) => {
    const mark = document.createElement("span");
    mark.className = `result-mark ${isCorrect ? "correct" : "incorrect"}`;
    mark.setAttribute("aria-label", isCorrect ? "Correct" : "Incorrect");
    return mark;
  }));
  const missedAnswers = answerResults.filter(({ isCorrect }) => !isCorrect);
  elements.missedReview.hidden = missedAnswers.length === 0;
  elements.missedReviewList.replaceChildren(...missedAnswers.map(({ question, choice }) => {
    const item = document.createElement("article");
    item.className = "missed-review-item";
    const category = document.createElement("span");
    category.className = "missed-review-category";
    category.textContent = question.category;
    const prompt = document.createElement("h3");
    prompt.textContent = question.question;
    const yourAnswer = document.createElement("p");
    yourAnswer.className = "missed-review-answer";
    yourAnswer.textContent = `Your answer: ${question[choice]}`;
    const correctAnswer = document.createElement("p");
    correctAnswer.className = "missed-review-correct";
    correctAnswer.textContent = `Correct answer: ${question[question.answer.trim().toUpperCase()]}`;
    const explanation = document.createElement("p");
    explanation.className = "missed-review-explanation";
    explanation.textContent = question.explanation;
    item.append(category, prompt, yourAnswer, correctAnswer, explanation);
    return item;
  }));
  elements.status.textContent = "ROUND COMPLETE";
  showScreen(elements.results);
  elements.resultTitle.focus();
}

elements.next.addEventListener("click", () => {
  if (questionIndex === QUESTIONS_PER_ROUND - 1) {
    showResults();
    return;
  }
  questionIndex += 1;
  updateScoreboard();
  renderQuestion();
  elements.questionText.focus();
});

document.querySelector("#start-button").addEventListener("click", startGame);
document.querySelector("#play-again-button").addEventListener("click", startGame);
document.querySelectorAll('input[name="difficulty"]').forEach((input) => {
  input.addEventListener("change", () => {
    elements.selectionError.hidden = true;
    updateQuestionPoolCount();
  });
});
document.querySelector("#reset-button").addEventListener("click", () => {
  correctAnswers = 0;
  scorePoints = 0;
  currentStreak = 0;
  questionIndex = 0;
  locked = false;
  elements.status.textContent = "READY WHEN YOU ARE";
  updateScoreboard();
  showScreen(elements.welcome);
  document.querySelector("#start-button").focus();
});

document.addEventListener("keydown", (event) => {
  if (elements.question.hidden || locked) return;
  const target = event.target;
  if (event.altKey || event.ctrlKey || event.metaKey || event.isComposing
    || target instanceof HTMLInputElement || target instanceof HTMLTextAreaElement
    || target instanceof HTMLSelectElement || target.isContentEditable) return;
  const choice = event.key.toUpperCase();
  if (CHOICES.includes(choice)) submitAnswer(choice);
});

loadPersonalBest();
fetch("questions.csv")
  .then((response) => {
    if (!response.ok) throw new Error(`Could not load questions.csv (${response.status}).`);
    return response.text();
  })
  .then((csvText) => {
    questions = parseCsv(csvText);
    const requiredFields = ["category", "question", ...CHOICES, "answer", "explanation", "difficulty"];
    if (questions.length === 0 || requiredFields.some((field) => !(field in questions[0]))) {
      throw new Error("The question file is empty or has missing columns.");
    }
    if (questions.some((question) => (
      requiredFields.some((field) => !question[field])
      || !CHOICES.includes(question.answer.toUpperCase())
      || !DIFFICULTIES.includes(question.difficulty)
    ))) {
      throw new Error("Each question needs complete fields, an A-D answer, and a valid difficulty.");
    }
    for (const difficulty of DIFFICULTIES) {
      if (questions.filter((question) => question.difficulty === difficulty).length < QUESTIONS_PER_ROUND) {
        throw new Error(`Add at least ${QUESTIONS_PER_ROUND} ${difficulty.toLowerCase()} questions to questions.csv.`);
      }
    }
    updateQuestionPoolCount();
    elements.loading.hidden = true;
    showScreen(elements.welcome);
  })
  .catch((error) => {
    console.error("Could not start the history trivia game.", error);
    elements.loading.hidden = true;
    elements.error.textContent = `Could not load the question bank: ${error.message}`;
    elements.error.hidden = false;
  });
