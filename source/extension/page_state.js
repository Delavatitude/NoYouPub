(() => {
  function videoId(value) {
    try {
      const url = new URL(value);
      if (url.protocol !== 'https:' || !['www.youtube.com','youtube.com'].includes(url.hostname)) return null;
      const id = url.pathname === '/watch' ? url.searchParams.get('v') : url.pathname.match(/^\/(?:shorts|live)\/([\w-]{11})$/)?.[1];
      return /^[\w-]{11}$/.test(id || '') ? id : null;
    } catch { return null; }
  }
  function sameVideo(left, right) {
    const id = videoId(left);
    return !!id && id === videoId(right);
  }
  function remoteForPage(pageURL, result, preference) {
    const state = result.state;
    const active = state ? state.owned && ['PLAYING','PAUSED','BUFFERING'].includes(state.player_state) : result.last?.active;
    return !!active && preference !== 'local' && sameVideo(pageURL, state?.video_url || result.last?.url);
  }
  function acceptsReply(replyURL, pageURL) {
    return !replyURL || sameVideo(replyURL, pageURL);
  }
  const api = {videoId, sameVideo, remoteForPage, acceptsReply};
  globalThis.NoYouPubPage = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})();
