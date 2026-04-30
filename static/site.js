const configNode = document.getElementById("app-config");

if (configNode) {
  const config = JSON.parse(configNode.textContent);
  const form = document.getElementById("plate-form");
  const questionsInput = document.getElementById("questions-input");
  const countInput = document.getElementById("count-input");
  const boardsRoot = document.getElementById("boards-root");
  const plateSummary = document.getElementById("plate-summary");
  const questionSummary = document.getElementById("question-summary");
  const errorNode = document.getElementById("form-error");
  const sampleButton = document.getElementById("sample-button");
  const downloadButton = document.getElementById("download-button");

  const state = {
    questionsText: config.sampleQuestionsText,
    count: config.defaultCount,
    generationSeed: config.initialPayload.generationSeed,
    boards: config.initialPayload.boards,
    questionCount: config.initialPayload.questionCount,
    isBusy: false,
  };

  const setError = (message = "") => {
    errorNode.textContent = message;
    errorNode.hidden = !message;
  };

  const setBusy = (busy) => {
    state.isBusy = busy;
    const submitButton = form.querySelector('button[type="submit"]');
    submitButton.disabled = busy;
    sampleButton.disabled = busy;
    downloadButton.disabled = busy;
  };

  const render = () => {
    questionsInput.value = state.questionsText;
    countInput.value = String(state.count);
    plateSummary.textContent = `${state.boards.length} plate${state.boards.length === 1 ? "" : "s"}`;
    questionSummary.textContent = `${state.questionCount} unique questions available`;
    boardsRoot.innerHTML = "";

    state.boards.forEach((board, boardIndex) => {
      const card = document.createElement("article");
      card.className = "plate-card";

      const header = document.createElement("div");
      header.className = "plate-card__header";
      header.innerHTML = `<span>Plate ${boardIndex + 1}</span><span>5x5</span>`;
      card.appendChild(header);

      const grid = document.createElement("div");
      grid.className = "plate-grid";

      board.forEach((label) => {
        const cell = document.createElement("div");
        cell.className = "plate-cell";
        if (label === "FREE") {
          cell.classList.add("plate-cell--free");
        }
        const text = document.createElement("span");
        text.textContent = label;
        cell.appendChild(text);
        grid.appendChild(cell);
      });

      card.appendChild(grid);
      boardsRoot.appendChild(card);
    });
  };

  const buildPayload = (reuseSeed) => ({
    questionsText: questionsInput.value,
    count: Number.parseInt(countInput.value, 10) || config.defaultCount,
    generationSeed: reuseSeed ? state.generationSeed : undefined,
  });

  const requestBoards = async () => {
    setBusy(true);
    setError();

    try {
      const response = await fetch(config.boardsUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
        },
        body: JSON.stringify(buildPayload(false)),
      });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.error || "Could not generate plates");
      }

      state.questionsText = questionsInput.value;
      state.count = payload.count;
      state.generationSeed = payload.generationSeed;
      state.boards = payload.boards;
      state.questionCount = payload.questionCount;
      render();
    } catch (error) {
      setError(error.message || "Could not generate plates");
    } finally {
      setBusy(false);
    }
  };

  const downloadPdf = async () => {
    setBusy(true);
    setError();

    try {
      const response = await fetch(config.pdfUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/pdf",
        },
        body: JSON.stringify(buildPayload(true)),
      });

      if (!response.ok) {
        const payload = await response.json();
        throw new Error(payload.error || "Could not build PDF");
      }

      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `bingo-plates-${state.count}.pdf`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    } catch (error) {
      setError(error.message || "Could not build PDF");
    } finally {
      setBusy(false);
    }
  };

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    await requestBoards();
  });

  sampleButton.addEventListener("click", () => {
    questionsInput.value = config.sampleQuestionsText;
    countInput.value = String(config.defaultCount);
    state.questionsText = config.sampleQuestionsText;
    state.count = config.defaultCount;
    setError();
  });

  downloadButton.addEventListener("click", async () => {
    await downloadPdf();
  });

  render();
}
