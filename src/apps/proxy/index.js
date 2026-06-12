// Choose the endpoint based on your PostHog project data residency
const POSTHOG_TARGET = "us.i.posthog.com"; // Change to "eu.i.posthog.com" if using EU residency

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    
    // 1. Rewrite the hostname to PostHog's ingestion servers
    url.hostname = POSTHOG_TARGET;
    
    // 2. Clone the request headers and update the Host header
    // This makes PostHog think the request came directly to them
    const newHeaders = new Headers(request.headers);
    newHeaders.set("Host", POSTHOG_TARGET);
    
    // 3. Create and send the modified request
    const modifiedRequest = new Request(url, {
      method: request.method,
      headers: newHeaders,
      body: request.body,
      redirect: "follow"
    });
    
    try {
      return await fetch(modifiedRequest);
    } catch (error) {
      return new Response("Proxy Error", { status: 502 });
    }
  }
};