#!/usr/bin/env python3

from .Exceptions import TriAllelicError

def Fst(alt_freq_i,alt_freq_j):
    '''
        Calculates Fst from alternate allele freqs
    '''
    if alt_freq_i == alt_freq_j == 1:
        return 0
    if alt_freq_i == alt_freq_j == 0:
        return 0
    ref_freq_i = 1 - alt_freq_i
    ref_freq_j = 1 - alt_freq_j
    # Calculate population heterozygosity
    H_i = 2 * alt_freq_i * ref_freq_i
    H_j = 2 * alt_freq_j * ref_freq_j
    H_s = (H_i + H_j) / 2
    # Calculate Average Allele Frequencies
    avg_alt_freq = (alt_freq_i + alt_freq_j)/2
    avg_ref_freq = (ref_freq_i + ref_freq_j)/2
    H_t = 2 * avg_alt_freq * avg_ref_freq
    # Return Fst
    return (H_t - H_s)/(H_t)

class Variant(object):
    genomap = { # shared genomap
        './.' : -1, '0/0' : 0, '0/1' : 1, '1/0' : 1, '1/1' : 2,
        -1 : -1, 0 : 0, 1 : 1, 2 : 2,
        '.|.' : -1, '0|0' : 0, '0|1' : 1, '1|0' : 1, '1|1' : 2,
    }
 
    def __init__(self, chrom, pos, id, ref, alt, qual='.', fltr='PASS', info='.', fmt='GT:GQ', genos=None):
        '''
        A fairly lightweight representation of a VCF compatible variant.        
            
        Parameters
        ----------
        chrom, pos, id, ref, alt, qual, filter, info, format, *genotypes
        
        Returns
        -------
        Variant instance    
        '''
        self.chrom = str(chrom)
        self.pos = int(pos)
        self.id = str(id)
        self.ref = str(ref)
        self.alt = str(alt)
        if qual != '.':
            self.qual = float(qual)
        else:
            self.qual = qual
        self.fltr = str(fltr)
        self.info = str(info)
        self.fmt = str(fmt)
        self.genos = genos

    @classmethod
    def from_str(cls,string):
        chrom,pos,id,ref,alt,qual,fltr,info,fmt,*genotypes = string.strip().split()
        self = cls(chrom,pos,id,ref,alt,qual,fltr,info,fmt,genos=genotypes)
        return self
    
    @classmethod
    def from_dict(cls,dict):
        chrom = dict['chrom']
        pos = int(dict['pos'])
        id = dict['id']
        ref = dict['ref']
        alt = dict['alt']
        qual = dict['qual']
        fltr = dict['fltr']
        info = dict['info']
        fmt = dict['fmt']
        genos = dict['genos']
        self = cls(chrom,pos,id,ref,alt,qual,fltr,info,fmt,genos=genos)
        return self
       
    @property
    def phased(self):
        ''' return bool on phase state '''
        if '|' in self.genos[0]:
            return True
        else:
            return False

    @property
    def biallelic(self):
        ''' return bool true if variant is biallelic '''
        if ',' in self.alt:
            return False
        else:
            return True
    
    def add_info(self,key,val):
        '''
        Add to the INFO field 
            
        Parameters
        ----------
        key:str
            The key of the info item
        val:str
            The value of the info item
                
        Returns
        -------
            None
        '''
        self.info += ";{}={}".format(key,val)

    def __getitem__(self,item):
        try:
            return self.__dict__[item]
        except KeyError as e:
            pass
        try:
            return self.genos[item]
        except KeyError as e:
            pass
        raise Exception("Value not found")

    def __repr__(self):
        return "<PonyTools Variant at: {} {}>".format(self.chrom,self.pos)

    def __str__(self):
        '''
            returns a string of variant suitable for VCF printing
        '''
        return "\t".join(map(str,[self.chrom, self.pos, self.id, self.ref, 
                    self.alt, self.qual, self.fltr, self.info, 
                    self.fmt ]+ self.genos ))

    def __eq__(self,var):
        if (self.chrom == var.chrom
            and self.pos == var.pos
            and self.id == var.id
            and self.ref == var.ref
            and self.alt == var.alt
            and self.qual == var.qual
            and self.fltr == var.fltr
            and self.info == var.info
            and self.fmt == var.fmt
            and self.genos == var.genos):
            return True
        else:  
            return False


    def alt_freq(self,samples_i=None,max_missing=0.3):
        '''
            Computes the ALTERNATE allele frequency.

            Parameters
            ----------
            samples_i : str iterable (individual ids)
                If not None, will compute MAF for subset of individuals.

        '''
        genos = self.genos()
        if samples_i is not None:
            genos = [genos[x] for x in samples_i]
        num_mis = sum([x.count('.') for x in genos])
        if (num_mis / (2*len(genos))) > max_missing:
            return None
        num_ref = sum([x.count('0') for x in genos])
        num_alt = sum([x.count('1') for x in genos])
        n = (2*len(genos)) - num_mis
        return num_alt/n

    def heterozygosity(self,samples_i=None,max_missing=0.3):
        '''
            Compute the heterozygositey of the SNP
            for indivduials indices in samples_i

            parameters
            ----------
            samples_i : int iterable (individual ids)
                If not None, will computer heterozygosity for 
                subset of individuals
        '''
        alt_freq = self.alt_freq(samples_i=samples_i,max_missing=max_missing)
        if alt_freq is None:
            return None
        ref_freq = 1 - alt_freq
        return 2 * alt_freq * ref_freq


    def alleles(self,samples_i=None,samples_id=None,format_field='GT',transform=None):
        ''' return alleles *in order* for samples '''
        if not transform:
            transform = lambda x:x
        if transform.__name__ == 'vcf2allele':
            transform = transform(self.ref,self.alt)
        gt_index = self.fmt.split(":").index(format_field)
        if samples_i:
            return [ transform(self.genos[sample_i].split(':')[gt_index]) for sample_i in samples_i]
        else:
            return [transform(geno.split(':')[gt_index]) for geno in self.genos]

    def r2(self,variant,samples_i,samples_j):
        ''' returns the r2 value with another variant '''
        # find common individuals
        geno1 = np.array(self.genos(transform=Allele.vcf2geno,samples_i=samples_i))
        geno2 = np.array(variant.genos(transform=Allele.vcf2geno,samples_i=samples_j))
        non_missing = (geno1!=-1)&(geno2!=-1)
        return (scipy.stats.pearsonr(geno1[non_missing],geno2[non_missing]))[0]**2
    
    def __sub__(self,variant):
        ''' returns the distance between SNPs '''
        if self.chrom != variant.chrom:
            return np.inf
        else:
            return abs(int(self.pos) - int(variant.pos))
    @property
    def is_polymorphic(self):
        if self.ref in ('A','C','G','T') and self.alt in ('A','C','G','T'):
            return True
        else:
            return False


    def conform(self,reference_genotype,GT_index=0,inplace=False):
        '''
            Conforms a variant to a reference genotype.

            Parameters
            ----------
            reference_genotype: str
                must be current alt or ref genotype. This
                becomes the new reference.

            Notes
            -----
            This happens IN PLACE.

        '''
        if self.alt == self.ref and self.ref != reference_genotype:
            # Sometimes PLINK will assign both the alt and reference
            # to the same thing, just make everyone alternate
            self.ref = reference_genotype
            # Make the translation table
            trans = str.maketrans(
                {'0':'1',
                 '1':'1'}
            )
            def conform_genotype(genotype):
                # split out the GT 
                fields = genotype.split(':')
                fields[GT_index] = str.translate(fields[GT_index],trans)
                return ':'.join(fields)
            self.genos = [conform_genotype(g) for g in self.genos]

        elif reference_genotype not in (self.alt,self.ref):
            raise TriAllelicError((
                'Cannot conform to genotype that is not one of'
                'the reference or alt {} != ({},{})'.format(
                    reference_genotype,
                    self.ref,
                    self.alt
                )
            ))
        elif not self.biallelic:
            raise TriAllelicError('cannot conform triallelic SNP: {}'.format(self.id))
        elif self.ref == reference_genotype:
            return self
        else:
            # Conform
            self.alt,self.ref = self.ref,self.alt
            # Make the translation table
            trans = str.maketrans(
                {'0':'1',
                 '1':'0'}
            )
            def conform_genotype(genotype):
                # split out the GT 
                fields = genotype.split(':')
                fields[GT_index] = str.translate(fields[GT_index],trans)
                return ':'.join(fields)
            self.genos = [conform_genotype(g) for g in self.genos]
        return self            
           

