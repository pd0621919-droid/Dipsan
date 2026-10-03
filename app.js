const $ = id => document.getElementById(id);

const api = $('api');

if (api) {
  api.value = localStorage.getItem('beast_api') || 'https://dipsan.onrender.com';
}

function show(pageId) {
  document.querySelectorAll('.page').forEach(page => {
    page.classList.remove('active');
  });

  const page = $(pageId);
  if (page) {
    page.classList.add('active');
  }

  document.querySelectorAll('#nav button[data-page]').forEach(button => {
    button.classList.toggle('active', button.dataset.page === pageId);
  });

  window.scrollTo({
    top: 0,
    behavior: 'smooth'
  });
}

/* Navigation */
document.querySelectorAll('[data-page]').forEach(button => {
  button.addEventListener('click', () => {
    show(button.dataset.page);
  });
});

/* Backend health */
if ($('health')) {
  $('health').addEventListener('click', async () => {
    try {
      const base =
        (api?.value || 'https://dipsan.onrender.com').replace(/\/$/, '');

      const response = await fetch(base + '/health');
      const data = await response.json();

      alert(
        data.ok
          ? 'Backend online • ' + (data.model || 'ready')
          : 'Backend responded'
      );
    } catch (error) {
      alert('Backend check failed: ' + error.message);
    }
  });
}

/* Save story */
if ($('saveStory')) {
  $('saveStory').addEventListener('click', () => {
    localStorage.setItem(
      'beast_story',
      JSON.stringify({
        series: $('series')?.value || '',
        premise: $('premise')?.value || '',
        powers: $('powers')?.value || ''
      })
    );

    if ($('storyMsg')) {
      $('storyMsg').textContent = 'Saved on this device.';
    }
  });
}

/* Save backend URL */
if ($('saveApi')) {
  $('saveApi').addEventListener('click', () => {
    const value =
      (api?.value || 'https://dipsan.onrender.com').replace(/\/$/, '');

    localStorage.setItem('beast_api', value);

    if ($('settingsMsg')) {
      $('settingsMsg').textContent = 'Backend URL saved.';
    }
  });
}

/* Clear local data */
if ($('clear')) {
  $('clear').addEventListener('click', () => {
    localStorage.clear();
    location.reload();
  });
}

/* Video generation */
async function gen(prompt, duration, ratio, outputId) {
  const output = $(outputId);

  if (!output) return;

  output.textContent = 'Generating…';

  try {
    const base =
      (api?.value || 'https://dipsan.onrender.com').replace(/\/$/, '');

    const response = await fetch(base + '/video/create', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        prompt: prompt,
        duration: Number(duration),
        resolution: '720p',
        aspect_ratio: ratio,
        audio: true
      })
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || 'Generation failed');
    }

    if (!data.video_url) {
      throw new Error('No video URL returned.');
    }

    output.innerHTML =
      '✅ Video created — ' +
      '<a target="_blank" rel="noopener" href="' +
      data.video_url +
      '">Open MP4</a><br>' +
      '<video controls src="' +
      data.video_url +
      '"></video>';

    return data;

  } catch (error) {
    output.textContent = '❌ ' + error.message;
  }
}

/* Scene generator */
if ($('sceneGen')) {
  $('sceneGen').addEventListener('click', () => {
    gen(
      'Type: ' +
        ($('type')?.value || '') +
        '. Intensity: ' +
        ($('intensity')?.value || '') +
        '. ' +
        ($('scenePrompt')?.value || ''),

      $('sceneDur')?.value || 8,

      $('ratio')?.value || '16:9',

      'sceneMsg'
    );
  });
}

/* Shorts generator */
if ($('shortGen')) {
  $('shortGen').addEventListener('click', () => {
    gen(
      $('shortPrompt')?.value || '',
      $('shortDur')?.value || 8,
      '9:16',
      'shortMsg'
    );
  });
}

/* Build long-video episode plan */
function build() {
  const minutes = Number($('longLen')?.value || 15);
  const sceneCount = Number($('count')?.value || 60);

  const totalSeconds = minutes * 60;

  const types = [
    'Cold open',
    'Mystery',
    'Comedy',
    'Symbol',
    'Rift',
    'Beast',
    'Fight',
    'Awakening',
    'Chase',
    'Emotion',
    'Ancient truth',
    'Cliffhanger'
  ];

  const plan = Array.from(
    { length: sceneCount },
    (_, index) => {
      const type = types[index % types.length];

      return {
        i: index + 1,
        type: type,
        seconds: Math.max(
          5,
          Math.round(totalSeconds / sceneCount)
        ),
        prompt:
          ($('epPrompt')?.value ||
            'Original Beastbound: Dimension Zero episode') +
          '. Scene ' +
          (index + 1) +
          ': ' +
          type +
          '. Original cinematic anime.'
      };
    }
  );

  localStorage.setItem(
    'episode_plan',
    JSON.stringify(plan)
  );

  render(plan);

  if ($('longMsg')) {
    $('longMsg').textContent =
      sceneCount +
      ' scenes planned for ' +
      minutes +
      ' minutes.';
  }

  return plan;
}

/* Render episode plan */
function render(plan) {
  const box = $('plan');

  if (!box) return;

  box.innerHTML = plan
    .map(
      scene =>
        '<div class="row">' +
        '<span><b>Scene ' +
        scene.i +
        '</b> — ' +
        scene.type +
        ' · ' +
        scene.seconds +
        's</span>' +
        '<button type="button" data-use="' +
        scene.i +
        '">Use</button>' +
        '</div>'
    )
    .join('');

  box.querySelectorAll('[data-use]').forEach(button => {
    button.addEventListener('click', () => {
      const index = Number(button.dataset.use) - 1;
      const scene = plan[index];

      if (!scene) return;

      if ($('scenePrompt')) {
        $('scenePrompt').value = scene.prompt;
      }

      /*
       * IMPORTANT:
       * The actual page ID is "scene", not "scenes".
       */
      show('scene');
    });
  });
}

/* Build button */
if ($('build')) {
  $('build').addEventListener('click', build);
}

/* Generate next long-video scene */
if ($('nextScene')) {
  $('nextScene').addEventListener('click', async () => {
    let plan = JSON.parse(
      localStorage.getItem('episode_plan') || 'null'
    );

    if (!plan || !plan.length) {
      plan = build();
    }

    const completed = Number(
      localStorage.getItem('done_scenes') || 0
    );

    const scene = plan[completed % plan.length];

    const result = await gen(
      scene.prompt,

      /*
       * Backend supports clips up to 16 seconds,
       * so each generated scene is capped at 16 seconds.
       */
      Math.min(
        16,
        Math.max(5, scene.seconds)
      ),

      '16:9',

      'longMsg'
    );

    if (result) {
      localStorage.setItem(
        'done_scenes',
        completed + 1
      );
    }
  });
}

/* Restore saved episode plan */
const savedPlan = localStorage.getItem(
  'episode_plan'
);

if (savedPlan) {
  try {
    render(JSON.parse(savedPlan));
  } catch (error) {
    console.log('Could not restore episode plan.');
  }
}

/* Audio + VFX plan */
if ($('saveAudio')) {
  $('saveAudio').addEventListener('click', () => {
    if ($('audioMsg')) {
      $('audioMsg').textContent =
        'Audio and VFX plan saved on this device.';
    }

    localStorage.setItem(
      'audio_plan',
      JSON.stringify({
        voice: $('voice')?.value || '',
        vfx: $('vfx')?.value || '',
        music: $('music')?.value || ''
      })
    );
  });
}

/* SEO generator */
if ($('seoGen')) {
  $('seoGen').addEventListener('click', () => {
    if ($('seoOut')) {
      $('seoOut').textContent =
        'TITLE\n' +
        ($('seoTitle')?.value || '') +
        '\n\nDESCRIPTION\n' +
        ($('seoDesc')?.value || '') +
        '\n\nTAGS\n' +
        'anime, original anime, Beastbound, Dimension Zero, anime story, anime fight, Beast Powers, dimensional rift, Hindi anime';
    }
  });
}

/* Show dashboard on first load */
show('dashboard');
