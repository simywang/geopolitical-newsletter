const API_KEYS = {
  en: process.env.BUTTONDOWN_API_KEY,
  nl: process.env.BUTTONDOWN_API_KEY_NL || process.env.BUTTONDOWN_API_KEY,
  zh: process.env.BUTTONDOWN_API_KEY_ZH || process.env.BUTTONDOWN_API_KEY,
};

export default async function handler(req, res) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const { email, lang = 'en' } = req.body;
  if (!email) {
    return res.status(400).json({ error: 'Email is required' });
  }

  const apiKey = API_KEYS[lang] || API_KEYS.en;
  if (!apiKey) {
    return res.status(500).json({ error: 'Server misconfigured' });
  }

  try {
    const bdResp = await fetch('https://api.buttondown.email/v1/subscribers', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Token ${apiKey}`,
      },
      body: JSON.stringify({ email_address: email }),
    });

    const data = await bdResp.json();

    if (bdResp.status === 201) {
      return res.status(201).json({ status: 'subscribed' });
    }

    const msg = JSON.stringify(data).toLowerCase();
    if (bdResp.status === 400 && (msg.includes('already') || msg.includes('duplicate'))) {
      return res.status(409).json({ status: 'already_subscribed' });
    }

    return res.status(400).json({ status: 'error', detail: data });
  } catch (e) {
    return res.status(500).json({ error: 'Network error' });
  }
}
