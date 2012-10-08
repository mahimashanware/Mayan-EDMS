from __future__ import absolute_import

import os
import tempfile
import re

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.core import management

from .literals import (FIXTURE_TYPES_CHOICES, FIXTURE_FILE_TYPE, COMMAND_LOADDATA)
from .managers import BootstrapSetupManager
from .classes import BootstrapModel, FixtureMetadata


class BootstrapSetup(models.Model):
    """
    Model to store the fixture for a pre configured setup.
    """
    name = models.CharField(max_length=128, verbose_name=_(u'name'), unique=True)
    description = models.TextField(verbose_name=_(u'description'), blank=True)
    fixture = models.TextField(verbose_name=_(u'fixture'), help_text=_(u'These are the actual database structure creation instructions.'))
    type = models.CharField(max_length=16, verbose_name=_(u'type'), choices=FIXTURE_TYPES_CHOICES)

    objects = BootstrapSetupManager()

    def __unicode__(self):
        return self.name

    def get_extension(self):
        """
        Return the fixture file extension based on the fixture type.
        """
        return FIXTURE_FILE_TYPE[self.type]

    def execute(self):
        """
        Read a bootstrap's fixture and create the corresponding model
        instances based on it.
        """
        BootstrapModel.check_for_data()
        handle, filepath = tempfile.mkstemp()
        # Just need the filepath, close the file description
        os.close(handle)

        filepath = os.path.extsep.join([filepath, self.get_extension()])

        with open(filepath, 'w') as file_handle:
            file_handle.write(self.cleaned_fixture)
        
        content = StringIO()
        management.call_command(COMMAND_LOADDATA, filepath, verbosity=0, stderr=content)
        content.seek(0, os.SEEK_END)
        if content.tell():
            content.seek(0)
            raise Exception(content.readlines()[-2])

        os.unlink(filepath)

    def compress(self):
        """
        Return a compacted and compressed version of the BootstrapSetup
        instance, meant for download.
        """
        return ''

    @property
    def cleaned_fixture(self):
        """
        Return the bootstrap setup's fixture without comments.
        """
        return re.sub(re.compile('#.*?\n'), '', self.fixture)

    def get_metadata_string(self):
        """
        Return all the metadata for the current bootstrap fixture.
        """
        return FixtureMetadata.generate_all(self)

    def save(self, *args, **kwargs):
        self.fixture = '%s\n\n%s' % (
            self.get_metadata_string(),
            self.cleaned_fixture
        )
        return super(BootstrapSetup, self).save(*args, **kwargs)

    class Meta:
        verbose_name = _(u'bootstrap setup')
        verbose_name_plural = _(u'bootstrap setups')
        ordering = ['name']
