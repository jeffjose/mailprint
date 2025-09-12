export default {
  async email(message, env, ctx) {
    try {
      // Parse email headers
      const headers = {};
      for (const [key, value] of message.headers) {
        headers[key.toLowerCase()] = value;
      }

      // Read the email body
      const reader = message.raw.getReader();
      const decoder = new TextDecoder();
      let rawEmail = '';
      
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        rawEmail += decoder.decode(value);
      }

      // Prepare the payload for telemetry.fyi
      const payload = {
        from: message.from,
        to: message.to,
        subject: headers.subject || '',
        headers: headers,
        raw: rawEmail,
        size: message.rawSize,
        timestamp: new Date().toISOString()
      };

      // Send to telemetry.fyi/email
      const response = await fetch('https://telemetry.fyi/email', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload)
      });

      if (!response.ok) {
        console.error(`Failed to forward email: ${response.status} ${response.statusText}`);
        message.setReject(`Failed to process email: ${response.status}`);
      }

    } catch (error) {
      console.error('Error processing email:', error);
      message.setReject(`Error processing email: ${error.message}`);
    }
  }
}