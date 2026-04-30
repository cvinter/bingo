const configNode = document.getElementById("app-config");

if (configNode) {
  const config = JSON.parse(configNode.textContent);
  const boardRoot = document.getElementById("bingo-board");
  const form = document.getElementById("generator-form");
  const seedInput = document.getElementById("seed-input");
  const seedLabel = document.getElementById("seed-label");
  const shuffleButton = document.getElementById("shuffle-button");
  const clearButton = document.getElementById("clear-button");

  const storageKey = (seed) => `bingo:${seed}`;

  const readMarks = (seed) => {
    try {
      const stored = window.localStorage.getItem(storageKey(seed));
      return stored ? JSON.parse(stored) : [];
    } catch {
      return [];
    }
  };

  const writeMarks = (seed, marks) => {
    window.localStorage.setItem(storageKey(seed), JSON.stringify([...marks]));
  };

  const randomSeed = () => Math.random().toString(36).slice(2, 8);

  const state = {
    seed: config.initialCard.seed,
    board: config.initialCard.board,
    marks: new Set(readMarks(config.initialCard.seed)),
  };

  const render = () => {
    boardRoot.innerHTML = "";
    seedLabel.textContent = state.seed;
    seedInput.value = state.seed;

    state.board.forEach((label, index) => {
      const cell = document.createElement("button");
      cell.type = "button";
      cell.className = "cell";
      if (label === "FREE") {
        cell.classList.add("cell--free", "cell--marked");
        cell.disabled = true;
      } else if (state.marks.has(index)) {
        cell.classList.add("cell--marked");
      }
      cell.setAttribute("aria-pressed", String(state.marks.has(index) || label === "FREE"));

      const text = document.createElement("span");
      text.textContent = label;
      cell.appendChild(text);

      cell.addEventListener("click", () => {
        if (label === "FREE") {
          return;
        }
        if (state.marks.has(index)) {
          state.marks.delete(index);
        } else {
          state.marks.add(index);
        }
        writeMarks(state.seed, state.marks);
        render();
      });

      boardRoot.appendChild(cell);
    });
  };

  const loadBoard = async (seed) => {
    const response = await fetch(`${config.apiUrl}?seed=${encodeURIComponent(seed)}`, {
      headers: {
        Accept: "application/json",
      },
    });
    if (!response.ok) {
      throw new Error("Failed to fetch board");
    }
    const payload = await response.json();
    state.seed = payload.seed;
    state.board = payload.board;
    state.marks = new Set(readMarks(payload.seed));
    render();
  };

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const nextSeed = seedInput.value.trim() || "bingo";
    await loadBoard(nextSeed);
  });

  shuffleButton.addEventListener("click", async () => {
    await loadBoard(randomSeed());
  });

  clearButton.addEventListener("click", () => {
    state.marks = new Set();
    writeMarks(state.seed, state.marks);
    render();
  });

  render();
}
