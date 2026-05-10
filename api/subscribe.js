const BD_API = 'https://api.buttondown.email/v1';

async function bdHeaders(apiKey) {
  return {
    'Content-Type': 'application/json',
    'Authorization': `Token ${apiKey}`,
  };
}

// Try to find a subscriber by email across all statuses (unsubscribed, removed, etc.)
async function findSubscriber(email, apiKey) {
  const headers = await bdHeaders(apiKey);
  const resp = await fetch(
    `${BD_API}/subscribers?email=${encodeURIComponent(email)}`,
    { headers }
  );
  if (!resp.ok) return null;
  const data = await resp.json();
  const results = data.results || [];
  return results.length > 0 ? results[0] : null;
}

// Reset a previously unsubscribed/removed subscriber to unactivated,
// so Buttondown sends them a fresh confirmation email
async function reactivateSubscriber(subscriberId, apiKey) {
  const headers = await bdHeaders(apiKey);
  const resp = await fetch(`${BD_API}/subscribers/${subscriberId}`, {
    method: 'PATCH',
    headers,
    body: JSON.stringify({ subscriber_type: 'unactivated' }),
  });
  return resp;
}

export default async function handler(req, res) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const { email } = req.body;
  if (!email) {
    return res.status(400).json({ error: 'Email is required' });
  }

  const apiKey = process.env.BUTTONDOWN_API_KEY;
  if (!apiKey) {
    return res.status(500).json({ error: 'Server misconfigured' });
  }

  const headers = await bdHeaders(apiKey);

  try {
    // Step 1: Try to create a new subscriber
    const bdResp = await fetch(`${BD_API}/subscribers`, {
      method: 'POST',
      headers,
      body: JSON.stringify({ email_address: email }),
    });

    const data = await bdResp.json();

    if (bdResp.status === 201) {
      return res.status(201).json({ status: 'subscribed' });
    }

    // Step 2: Creation failed — check if this email already exists (any status)
    const existing = await findSubscriber(email, apiKey);

    if (existing) {
      const type = existing.subscriber_type || '';

      // Already active subscriber
      if (type === 'regular' || type === 'unactivated') {
        return res.status(409).json({ status: 'already_subscribed' });
      }

      // Previously unsubscribed or removed — reset to unactivated so they
      // receive a fresh confirmation email (same experience as a new subscriber)
      const patchResp = await reactivateSubscriber(existing.id, apiKey);
      if (patchResp.ok) {
        return res.status(201).json({ status: 'subscribed' });
      }
    }

    // Step 3: Unknown error
    return res.status(400).json({ status: 'error', detail: data });
  } catch (e) {
    return res.status(500).json({ error: 'Network error' });
  }
}
