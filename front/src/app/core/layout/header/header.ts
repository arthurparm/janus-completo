import { Component, inject } from '@angular/core';
import { RouterLink, RouterLinkActive } from '@angular/router';
import { AuthService } from '../../auth/auth.service';
import { CommonModule } from '@angular/common';
import { JarvisAvatarComponent } from '../../../shared/components/jarvis-avatar/jarvis-avatar.component';
import { Database, objectVal, ref } from '@angular/fire/database';
import { Observable } from 'rxjs';

@Component({
  selector: 'app-header',
  standalone: true,
  imports: [RouterLink, RouterLinkActive, CommonModule, JarvisAvatarComponent],
  templateUrl: './header.html',
  styleUrl: './header.scss'
})
export class Header {
  private auth = inject(AuthService);
  private db = inject(Database);

  isMenuOpen = false;
  isAuthenticated$ = this.auth.isAuthenticated$;

  metrics$: Observable<any>;

  constructor() {
    this.metrics$ = objectVal(ref(this.db, 'system/metrics'));
  }

  toggleMenu() {
    this.isMenuOpen = !this.isMenuOpen;
  }

  closeMenu() {
    this.isMenuOpen = false;
  }

  logout() {
    this.auth.logout();
  }
}
