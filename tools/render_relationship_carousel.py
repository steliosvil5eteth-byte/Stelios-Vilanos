#!/usr/bin/env python3
"""Render the relationship-change carousel with its established CTA.
Uses the deterministic zero-cost carousel renderer; no paid generation APIs.
"""
import render_carousel_pack as base

base.CTA = 'Η γνώμη σας μετράει. Ακολούθησέ με για περισσότερα.'

if __name__ == '__main__':
    base.main()
