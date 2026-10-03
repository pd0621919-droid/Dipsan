const apiInput = document.getElementById("api");

apiInput.value =
  localStorage.getItem("beast_api_url") ||
  "https://dipsan.onrender.com";

document.getElementById("save").onclick = () => {
  localStorage.setItem(
    "beast_api_url",
    apiInput.value.replace(/\/$/, "")
  );

  document.getElementById("status").textContent =
    "Backend URL saved.";
};

document.getElementById("generate").onclick = async () => {
  const status = document.getElementById("status");
  const api = apiInput.value.replace(/\/$/, "");

  status.textContent =
    "Generating your Beastbound scene…";

  try {
    const response = await fetch(
      api + "/video/create",
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          prompt: document.getElementById("prompt").value,
          duration: Number(
            document.getElementById("duration").value
          ),
          resolution: "720p",
          aspect_ratio:
            document.getElementById("ratio").value,
          audio: true
        })
      }
    );

    const data = await response.json();

    if (!response.ok) {
      throw new Error(
        data.detail || "Generation failed"
      );
    }

    if (data.video_url) {
      status.innerHTML =
        "<b>✅ Video created!</b><br>" +
        '<a href="' +
        data.video_url +
        '" target="_blank">Open MP4</a>' +
        '<video class="video" controls src="' +
        data.video_url +
        '"></video>';
    } else {
      status.textContent =
        JSON.stringify(data, null, 2);
    }

  } catch (error) {
    status.textContent =
      "❌ " + error.message;
  }
};
