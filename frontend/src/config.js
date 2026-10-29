// Sab details yahin badalni hain. Baaki code ko chhune ki zaroorat nahi.
import couple from './assets/couple.png'

// Couple photo: replace public/BH.jpg with your image. No code changes needed.
// If the file is missing, the invitation falls back to the included illustration.
const hero = '/BH.png'
const pick = (files) => Object.values(files)[0] ?? null
const venue = pick(import.meta.glob('./assets/Venue.jpeg', { eager: true, import: 'default' }))
export const IMG = { couple, hero, venue }

export const GROOM = 'Bhavesh'
export const BRIDE = 'Heena'
export const WEDDING_DATE = '2026-12-03T08:15:00+05:30' // countdown target

export const VENUE = {
  name: 'Khaki Resort',
  line1: 'NH 162, Opposite HP Petrol Pump, Village Barr',
  line2: 'Dist. Pali, Rajasthan',
  mapUrl:
    'https://www.google.com/maps/search/?api=1&query=' +
    encodeURIComponent(' NH. 162, Opp. HP Petrol Pump, Village Barr, Pali District, Beawar, Rajasthan 306105'),
}

export const CALENDAR_URL =
  'https://calendar.google.com/calendar/render?action=TEMPLATE&text=' +
  encodeURIComponent('Bhavesh & Heena - Shubh Vivah') +
  '&dates=20261203T024500Z/20261203T035500Z&location=' +
  encodeURIComponent('Khaki Resort, NH-162, Village Barr, Pali, Rajasthan')

export const EVENTS = [
  ['Vinayak Sthapana', 'Sunday, 29 November 2026 · 10:30 AM'],
  ['Mayra Ceremony', 'Wednesday, 2 December 2026 · 10:00 AM'],
  ['Haldi Ceremony', 'Wednesday, 2 December 2026 · 3:00 PM'],
  ['Mehendi Ceremony', 'Wednesday, 2 December 2026 · 7:00 PM'],
  ['Ganpati Sthapana', 'Wednesday, 2 December 2026 · 8:30 PM'],
  ['Bharat Swagat', 'Thursday, 3 December 2026 · 7:50 AM'],
  ['Shubh Vivah (Wedding)', 'Thursday, 3 December 2026 · 8:15 AM onwards'],
  ['Ashirwad Samaroh', 'Thursday, 3 December 2026 · 7:30 PM'],
  ['Preetibhoj (Wedding Feast)', 'Thursday, 3 December 2026 · 7:00 PM onwards'],
]
export const whatsapp = (text) => 'https://wa.me/?text=' + encodeURIComponent(text)

// Separate backend deployment URL. Set VITE_API_BASE_URL in frontend Vercel settings.
export const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'https://backend-wedding-red.vercel.app').replace(/\/$/, '')
export const apiUrl = (path) => `${API_BASE_URL}${path.startsWith('/') ? path : `/${path}`}`
