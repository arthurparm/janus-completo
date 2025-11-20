import {Component, inject} from '@angular/core';
import {RouterLink, RouterLinkActive, Router} from '@angular/router';
import {AuthService} from '../../auth/auth.service';
import {AUTH_TOKEN_KEY} from '../../../services/api.config';

@Component({
  selector: 'app-header',
  imports: [RouterLink, RouterLinkActive],
  templateUrl: './header.html',
  styleUrl: './header.scss'
})
export class Header {
  private auth = inject(AuthService)
  private router = inject(Router)
  isMenuOpen = false;

  get isAuthenticated(): boolean {
    return !!localStorage.getItem(AUTH_TOKEN_KEY)
  }

  toggleMenu() { this.isMenuOpen = !this.isMenuOpen; }
  closeMenu() { this.isMenuOpen = false; }

  async logout() {
    this.auth.logout()
    await this.router.navigate(['/login'])
  }
}
