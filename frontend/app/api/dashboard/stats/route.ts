import { NextRequest, NextResponse } from 'next/server';
import { apiJSON } from '@/lib/api-client';
import { DashboardStats } from '@/types/dashboard';

export async function GET(request: NextRequest) {
  try {
    const stats = await apiJSON<DashboardStats>('/api/v1/stats/');
    return NextResponse.json(stats);
  } catch (error) {
    console.error('Failed to fetch dashboard stats via BFF:', error);
    return NextResponse.json(
      { error: 'Failed to fetch dashboard stats' },
      { status: 500 }
    );
  }
}
