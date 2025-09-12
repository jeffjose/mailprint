export default {
  async email(message, env, ctx) {
    console.log(`📧 Worker v2.0 - Received email from: ${message.from} to: ${message.to}`);
    
    try {
      // Parse email headers
      const headers = {};
      for (const [key, value] of message.headers) {
        headers[key.toLowerCase()] = value;
      }

      console.log(`📋 Subject: ${headers.subject || '(no subject)'}`);

      // Read the email body
      const reader = message.raw.getReader();
      const decoder = new TextDecoder();
      let rawEmail = '';
      
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        rawEmail += decoder.decode(value);
      }

      console.log(`📏 Email size: ${message.rawSize} bytes`);

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

      console.log(`🚀 Forwarding to: https://telemetry.fyi/email`);

      // Send to telemetry.fyi/email
      const response = await fetch('https://telemetry.fyi/email', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload)
      });

      if (!response.ok) {
        console.error(`❌ Failed to forward email: ${response.status} ${response.statusText}`);
        const errorBody = await response.text();
        console.error(`Response body: ${errorBody}`);
        // Don't reject - just log the error
        // message.setReject(`Failed to process email: ${response.status}`);
      } else {
        console.log(`✅ Email forwarded successfully: ${response.status}`);
      }

    } catch (error) {
      console.error('❌ Error processing email:', error);
      console.error('Stack trace:', error.stack);
      // Don't reject - just log the error
      // message.setReject(`Error processing email: ${error.message}`);
    }
  }
}