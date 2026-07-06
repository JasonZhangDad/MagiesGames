import { defineStore } from 'pinia'
import { api, getToken, setToken } from '../api'

export const useUserStore = defineStore('user', {
  state: () => ({
    token: getToken(),
    profile: null,
  }),
  actions: {
    async guestLogin(nickname) {
      this._apply(await api.guest(nickname))
    },
    async register(username, password, nickname) {
      this._apply(await api.register(username, password, nickname))
    },
    async login(username, password) {
      this._apply(await api.login(username, password))
    },
    _apply({ token, user }) {
      setToken(token)
      this.token = token
      this.profile = user
    },
    async fetchMe() {
      if (!this.token) return null
      try {
        this.profile = await api.me()
      } catch {
        this.logout()
      }
      return this.profile
    },
    logout() {
      setToken(null)
      this.token = null
      this.profile = null
    },
  },
})
