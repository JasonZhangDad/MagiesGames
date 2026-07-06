import { defineStore } from 'pinia'
import { api, getToken, setToken } from '../api'

export const useUserStore = defineStore('user', {
  state: () => ({
    token: getToken(),
    profile: null,
  }),
  actions: {
    async guestLogin(nickname) {
      const { token, user } = await api.guest(nickname)
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
