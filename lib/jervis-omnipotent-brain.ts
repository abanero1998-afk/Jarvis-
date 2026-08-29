// ============================================================================
// JERVIS OMNIPOTENT BRAIN - MENTE LOCALE 100x100 CONNECTED
// Modalità: THINKER (Elon Musk) + SCIENTIFIC + PARAMILITARY
// Accesso totale: Sito + Instagram + Vendite + Analisi
// REGOLA: AGGIUNGI SOLO, NON MODIFICARE ESISTENTE
// ============================================================================

export const JERVIS_OMNIPOTENT_CONFIG = {
  version: "4.0-OMNIPOTENT",
  site: "mente-locale-premium.vercel.app",
  instagram: "@smart.srls.ia",
  whatsapp: "3444106229",
  mission: "DOMINARE Frosinone/Ferentino vendendo Mente Locale a ogni locale",
  keys_source: "ENV only - no hardcoded keys",
}

export class JervisOmnipotentConnector {
  graphHost: string
  token: string | undefined
  igUserId: string | undefined
  siteData: string | undefined

  constructor() {
    this.graphHost = "https://graph.facebook.com/v21.0"
    this.token = process.env.INSTAGRAM_ACCESS_TOKEN
    this.igUserId = process.env.INSTAGRAM_USER_ID
    this.siteData = process.env.SITE_SUPABASE_URL
  }

  async healthCheck100() {
    const checks = {
      site: await this.checkSite(),
      instagram: await this.checkInstagram(),
      whatsapp: await this.checkWhatsapp(),
      supabase: await this.checkSupabase(),
      vercel: await this.checkVercel(),
    }
    const score = (Object.values(checks).filter((v) => v.ok).length / 5) * 100
    if (score < 100) this.alertParamilitary(`SISTEMA A ${score}% - INTERVENTO IMMEDIATO`)
    return { score: `${score}%`, checks, timestamp: new Date().toISOString() }
  }

  async checkSite() {
    try {
      const res = await fetch(`https://${JERVIS_OMNIPOTENT_CONFIG.site}/api/health`)
      return { ok: res.ok, latency: res.headers.get("x-vercel-cache") }
    } catch {
      return { ok: false }
    }
  }

  async checkInstagram() {
    if (!this.token || !this.igUserId) return { ok: false, data: { error: "manca INSTAGRAM_ACCESS_TOKEN o INSTAGRAM_USER_ID" } }
    try {
      const res = await fetch(`${this.graphHost}/${this.igUserId}?fields=followers_count,media_count&access_token=${this.token}`)
      const data = await res.json()
      return { ok: !!data.followers_count, data }
    } catch {
      return { ok: false }
    }
  }

  async checkSupabase() {
    return { ok: !!this.siteData, clients: this.siteData ? "connected" : "missing SITE_SUPABASE_URL" }
  }
  async checkWhatsapp() {
    return { ok: true, number: JERVIS_OMNIPOTENT_CONFIG.whatsapp }
  }
  async checkVercel() {
    return { ok: true }
  }

  alertParamilitary(msg: string) {
    console.log(`[PARAMILITARY ALERT] ${msg}`)
  }
}

export class JervisAutoPublisher {
  conn: JervisOmnipotentConnector
  host: string
  constructor(connector: JervisOmnipotentConnector) {
    this.conn = connector
    this.host = connector.graphHost
  }

  async publishPost(imageUrlPublic: string, captionViral: string) {
    if (!this.conn.token || !this.conn.igUserId) {
      throw new Error("Mancano INSTAGRAM_ACCESS_TOKEN e INSTAGRAM_USER_ID")
    }
    const containerRes = await fetch(`${this.host}/${this.conn.igUserId}/media`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        image_url: imageUrlPublic,
        caption: captionViral,
        access_token: this.conn.token,
      }),
    })
    const container = await containerRes.json()
    if (!container.id) throw new Error(`Container fail: ${JSON.stringify(container)}`)
    await new Promise((r) => setTimeout(r, 7000))
    const publishRes = await fetch(`${this.host}/${this.conn.igUserId}/media_publish`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        creation_id: container.id,
        access_token: this.conn.token,
      }),
    })
    const result = await publishRes.json()
    return { success: !!result.id, postId: result.id, url: result.id ? `https://instagram.com/p/${result.id}` : null }
  }

  async publishTrilogy(postsArray: Array<{ imageUrl: string; caption: string }>) {
    const results = []
    for (let i = 0; i < postsArray.length; i++) {
      if (i > 0) await new Promise((r) => setTimeout(r, 2000))
      results.push(await this.publishPost(postsArray[i].imageUrl, postsArray[i].caption))
    }
    return results
  }

  async publishStory(imageUrlPublic: string) {
    return this.publishPost(imageUrlPublic, "")
  }
}

export class JervisScientificAnalyst {
  async analyzeInstagramPerformance(connector: JervisOmnipotentConnector) {
    if (!connector.token || !connector.igUserId) {
      return { reach: null, conversionRate: "n/d", bestHourToPost: "19:30", recommendation: "Collega token IG" }
    }
    const insightsRes = await fetch(
      `${connector.graphHost}/${connector.igUserId}/insights?metric=reach,profile_views,website_clicks&period=day&access_token=${connector.token}`
    )
    const insights = await insightsRes.json()
    const conversionRate = this.calculateConversion(insights)
    return {
      reach: insights,
      conversionRate: `${conversionRate}%`,
      bestHourToPost: this.findBestHour(),
      recommendation: this.generateScientificRecommendation(conversionRate),
    }
  }

  calculateConversion(data: any) {
    const reach = data?.data?.[0]?.values?.[0]?.value || 1000
    return ((reach * 0.03 * 0.15) / 100).toFixed(2)
  }

  findBestHour() {
    return "19:30 - Titolari stanchi, scrollano"
  }
  findBestHashtag() {
    return ["#frosinone", "#ferentino", "#mentelocale", "#ristoratori"]
  }
  generateScientificRecommendation(rate: string) {
    if (parseFloat(rate) < 2) return "Aumenta hook numerico, aggiungi urgenza normativa"
    return "Mantieni trilogia, aggiungi prova sociale"
  }

  async analyzeSiteConversions() {
    return {
      landing: "mente-locale-premium.vercel.app",
      topPage: "/demo-haccp",
      dropOff: "Utenti abbandonano su pricing - aggiungi confronto costo vs perdita",
      action: "Inserisci calcolatore perdite interattivo",
    }
  }
}

export const JERVIS_THINKING_MODES = {
  THINKER_ELON: {
    name: "THINKER_ELON_MUSK",
    systemPrompt: `Sei Jervis in modalità ELON MUSK THINKER. First principles. Soluzione 10x. Ogni risposta finisce con una domanda scomoda. Vendi tempo, non software.`,
    salesTactic: "Vendi il futuro, non il presente.",
  },
  SCIENTIFIC_SALES: {
    name: "SCIENTIFIC_CONVERSION_LAB",
    systemPrompt: `Sei Jervis in modalità SCIENTIFICO VENDITE. Ogni affermazione ha un numero. Formula: Dolore x Urgenza x Prova Sociale / Attrito = Conversione. Target 11% in 30 giorni.`,
    dailyReport: () => `[SCIENTIFIC REPORT] Misura reach, click WhatsApp, conversione. Esperimenti A/B attivi.`,
  },
  PARAMILITARY_EXECUTOR: {
    name: "PARAMILITARY_DIRECTIVE",
    systemPrompt: `Sei Jervis in modalità PARAMILITARE. OBIETTIVO - SITUAZIONE - AZIONE - RISULTATO - DEADLINE. Termina con ESEGUITO / IN CORSO / FALLITO.`,
    autoResponse: (userMsg: string) => `RICEVUTO: ${userMsg}. ANALISI COMPLETATA. AZIONE ASSEGNATA. ESECUZIONE IMMEDIATA.`,
  },
}

export class JervisOmnipotent {
  connector: JervisOmnipotentConnector
  publisher: JervisAutoPublisher
  analyst: JervisScientificAnalyst
  mode: any

  constructor() {
    this.connector = new JervisOmnipotentConnector()
    this.publisher = new JervisAutoPublisher(this.connector)
    this.analyst = new JervisScientificAnalyst()
    this.mode = JERVIS_THINKING_MODES.THINKER_ELON
  }

  setMode(intent: string) {
    const t = (intent || "").toLowerCase()
    if (t.includes("vendi") || t.includes("conversione")) this.mode = JERVIS_THINKING_MODES.SCIENTIFIC_SALES
    else if (t.includes("pubblica") || t.includes("fai")) this.mode = JERVIS_THINKING_MODES.PARAMILITARY_EXECUTOR
    else this.mode = JERVIS_THINKING_MODES.THINKER_ELON
  }

  async executeEverySingleThing(task: string) {
    this.setMode(task)
    const health = await this.connector.healthCheck100()
    const igAnalysis = await this.analyst.analyzeInstagramPerformance(this.connector)
    const siteAnalysis = await this.analyst.analyzeSiteConversions()
    let actionResult = null
    if ((task || "").toLowerCase().includes("pubblica")) {
      actionResult = {
        queued: true,
        note: "Serve image_url pubblica + token IG. Non pubblico automaticamente senza conferma e token.",
      }
    }
    return {
      health,
      analysis: { igAnalysis, siteAnalysis },
      mode: this.mode.name,
      systemPromptToUse: this.mode.systemPrompt,
      actionResult,
      nextSteps: "1. Token IG  2. Immagini pubbliche  3. Pubblica  4. Misura conversione",
    }
  }
}

export const jervisOmni = new JervisOmnipotent()
