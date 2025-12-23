import { Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { Header } from '../header/header';
import { Sidebar } from '../sidebar/sidebar';
import { NotificationBanner } from '../../notifications/notification-banner';

@Component({
  selector: 'app-main-layout',
  standalone: true,
  imports: [RouterOutlet, Header, Sidebar, NotificationBanner],
  templateUrl: './main-layout.html',
  styleUrl: './main-layout.scss'
})
export class MainLayout { }